# agents/ec2_agent/rules/intent_conversion_rule.py

import boto3
from botocore.exceptions import ClientError


class EC2IntentConversionRule:
    """
    Rule to handle intent conflicts - when user specifies one intent 
    but EC2 configuration conflicts with that intent.
    """
    
    id = "ec2_intent_conversion"
    detection = "EC2 configuration conflicts with user intent"
    auto_safe = False  # Always manual review for intent conflicts
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = False
        self.fix_type = None
        self.conflict_details = None
        self.intent_confidence = 0.0
    
    def check_with_intent(self, client, instance_id, intent, recommendations):
        """Check for intent vs configuration conflicts."""
        conflicts = []
        
        from agents.ec2_agent.intent_detector import EC2Intent
        
        # Get instance details
        try:
            response = client.describe_instances(InstanceIds=[instance_id])
            if not response['Reservations']:
                return False
            
            instance = response['Reservations'][0]['Instances'][0]
        except Exception as e:
            print(f"Error getting instance details: {e}")
            return False
        
        # Check different types of intent conflicts
        if intent == EC2Intent.WEB_SERVER:
            web_conflicts = self._check_web_server_conflicts(client, instance_id, instance)
            conflicts.extend(web_conflicts)
        
        elif intent == EC2Intent.DATABASE_SERVER:
            db_conflicts = self._check_database_conflicts(client, instance_id, instance)
            conflicts.extend(db_conflicts)
        
        elif intent == EC2Intent.DEVELOPMENT_TESTING:
            dev_conflicts = self._check_development_conflicts(client, instance_id, instance)
            conflicts.extend(dev_conflicts)
        
        elif intent == EC2Intent.BASTION_HOST:
            bastion_conflicts = self._check_bastion_conflicts(client, instance_id, instance)
            conflicts.extend(bastion_conflicts)
        
        if conflicts:
            self.conflict_details = conflicts
            self._set_conversion_instructions(conflicts[0], intent, instance_id)
            print(f"⚠️ Intent conflict: User wants {intent.value} but found {len(conflicts)} configuration conflicts")
            return True
        
        return False
    
    def _check_web_server_conflicts(self, client, instance_id, instance):
        """Check for conflicts with web server intent."""
        conflicts = []
        
        try:
            # Check if web ports are blocked
            sg_ids = [sg['GroupId'] for sg in instance.get('SecurityGroups', [])]
            if sg_ids:
                sg_response = client.describe_security_groups(GroupIds=sg_ids)
                
                has_http = False
                has_https = False
                
                for sg in sg_response['SecurityGroups']:
                    for rule in sg.get('IpPermissions', []):
                        from_port = rule.get('FromPort')
                        to_port = rule.get('ToPort')
                        
                        if from_port == 80 or (from_port <= 80 <= to_port):
                            has_http = True
                        if from_port == 443 or (from_port <= 443 <= to_port):
                            has_https = True
                
                if not has_http and not has_https:
                    conflicts.append({
                        "type": "web_ports_blocked",
                        "current_config": "No HTTP (80) or HTTPS (443) ports open in security groups",
                        "user_intent": "web_server",
                        "instance_id": instance_id,
                        "recommendation": "Open HTTP and/or HTTPS ports in security groups"
                    })
            
            # Check if instance is in private subnet without load balancer
            if not instance.get('PublicIpAddress'):
                conflicts.append({
                    "type": "web_server_private_only",
                    "current_config": "Web server has no public IP address",
                    "user_intent": "web_server",
                    "instance_id": instance_id,
                    "recommendation": "Add public IP or use Application Load Balancer"
                })
        
        except ClientError as e:
            print(f"Error checking web server conflicts: {e}")
        
        return conflicts
    
    def _check_database_conflicts(self, client, instance_id, instance):
        """Check for conflicts with database server intent."""
        conflicts = []
        
        try:
            # Check if database has public IP (security risk)
            if instance.get('PublicIpAddress'):
                conflicts.append({
                    "type": "database_public_access",
                    "current_config": "Database server has public IP address",
                    "user_intent": "database_server",
                    "instance_id": instance_id,
                    "recommendation": "Move database to private subnet, access via application servers only"
                })
            
            # Check instance type suitability
            instance_type = instance.get('InstanceType', '')
            if not any(db_type in instance_type for db_type in ['r5', 'r6', 'r4', 'm5', 'm6i']):
                conflicts.append({
                    "type": "inappropriate_instance_type",
                    "current_config": f"Using {instance_type} for database workload",
                    "user_intent": "database_server",
                    "instance_id": instance_id,
                    "recommendation": "Use memory-optimized instances (r5, r6) for database workloads"
                })
        
        except Exception as e:
            print(f"Error checking database conflicts: {e}")
        
        return conflicts
    
    def _check_development_conflicts(self, client, instance_id, instance):
        """Check for conflicts with development testing intent."""
        conflicts = []
        
        try:
            # Check if using expensive instance types for development
            instance_type = instance.get('InstanceType', '')
            expensive_types = ['p3', 'p4', 'x1', 'r5.large', 'r5.xlarge', 'm5.large', 'm5.xlarge']
            
            if any(exp_type in instance_type for exp_type in expensive_types):
                conflicts.append({
                    "type": "expensive_dev_instance",
                    "current_config": f"Using expensive instance type {instance_type} for development",
                    "user_intent": "development_testing",
                    "instance_id": instance_id,
                    "recommendation": "Use smaller, burstable instances (t3.micro, t3.small) for development"
                })
            
            # Check if running 24/7 (cost waste for dev)
            state = instance.get('State', {}).get('Name')
            if state == 'running':
                # This would need additional logic to determine if it's been running continuously
                # For now, just flag as potential optimization
                conflicts.append({
                    "type": "dev_instance_always_running",
                    "current_config": "Development instance appears to run continuously",
                    "user_intent": "development_testing",
                    "instance_id": instance_id,
                    "recommendation": "Use Instance Scheduler to stop/start automatically or consider Spot instances"
                })
        
        except Exception as e:
            print(f"Error checking development conflicts: {e}")
        
        return conflicts
    
    def _check_bastion_conflicts(self, client, instance_id, instance):
        """Check for conflicts with bastion host intent."""
        conflicts = []
        
        try:
            # Check if SSH is not properly restricted
            sg_ids = [sg['GroupId'] for sg in instance.get('SecurityGroups', [])]
            if sg_ids:
                sg_response = client.describe_security_groups(GroupIds=sg_ids)
                
                ssh_open_to_world = False
                for sg in sg_response['SecurityGroups']:
                    for rule in sg.get('IpPermissions', []):
                        if rule.get('FromPort') == 22:
                            for ip_range in rule.get('IpRanges', []):
                                if ip_range.get('CidrIp') == '0.0.0.0/0':
                                    ssh_open_to_world = True
                                    break
                
                if ssh_open_to_world:
                    conflicts.append({
                        "type": "bastion_ssh_unrestricted",
                        "current_config": "SSH (port 22) open to 0.0.0.0/0",
                        "user_intent": "bastion_host",
                        "instance_id": instance_id,
                        "recommendation": "Restrict SSH access to specific IP ranges or use AWS Systems Manager Session Manager"
                    })
        
        except Exception as e:
            print(f"Error checking bastion conflicts: {e}")
        
        return conflicts
    
    def _set_conversion_instructions(self, conflict, intent, instance_id):
        """Set specific instructions based on conflict type and intent."""
        
        if conflict["type"] == "web_ports_blocked":
            self.fix_instructions = [
                f"Current: {conflict['current_config']}",
                f"User Intent: {conflict['user_intent']}",
                "",
                "🔧 Web Server Configuration Steps:",
                "1. Navigate to EC2 > Security Groups",
                "2. Select security group attached to the instance",
                "3. Edit inbound rules to add:",
                "   - HTTP: Port 80, Source 0.0.0.0/0 (for public web access)",
                "   - HTTPS: Port 443, Source 0.0.0.0/0 (for secure web access)",
                "4. Install and configure web server software (Apache, Nginx, etc.)",
                "5. Test web server accessibility",
                "",
                "💡 Alternative: Use Application Load Balancer for better scalability"
            ]
            self.can_auto_fix = True  # Can safely open web ports
            self.fix_type = "configure_web_server_access"
        
        elif conflict["type"] == "database_public_access":
            self.fix_instructions = [
                f"Current: {conflict['current_config']}",
                f"User Intent: {conflict['user_intent']}",
                "",
                "🔧 Database Security Configuration:",
                "1. Create or identify a private subnet",
                "2. Stop the database instance",
                "3. Modify instance to move to private subnet",
                "4. Update security groups to allow access only from application subnets",
                "5. Update application connection strings to use private IP",
                "6. Test database connectivity from application servers",
                "",
                "⚠️ This will require application configuration changes"
            ]
            self.can_auto_fix = False  # Requires network changes
            self.fix_type = "move_database_to_private_subnet"
        
        elif conflict["type"] == "expensive_dev_instance":
            self.fix_instructions = [
                f"Current: {conflict['current_config']}",
                f"User Intent: {conflict['user_intent']}",
                "",
                "🔧 Development Instance Optimization:",
                "1. Create AMI of current instance",
                "2. Launch new instance with t3.micro or t3.small",
                "3. Test development workload on smaller instance",
                "4. Terminate original instance if tests pass",
                "5. Set up Instance Scheduler for automatic stop/start",
                "",
                "💰 Estimated savings: 50-80% on compute costs"
            ]
            self.can_auto_fix = False  # Requires testing
            self.fix_type = "optimize_dev_instance_type"
        
        else:
            self.fix_instructions = [
                f"Current: {conflict['current_config']}",
                f"User Intent: {conflict['user_intent']}",
                "",
                "🔧 Resolution Steps:",
                f"1. {conflict['recommendation']}",
                "2. Test changes in development environment first",
                "3. Apply changes to production instance",
                "4. Monitor for issues",
                "",
                "⚠️ Changes may affect instance functionality"
            ]
            self.can_auto_fix = False
            self.fix_type = "manual_intent_alignment"
    
    def check(self, client, instance_id):
        """Legacy check method - not used for intent conversion."""
        return False
    
    def fix(self, client, instance_id):
        """Fix intent conversion conflicts."""
        if not self.conflict_details:
            return {"success": False, "message": "No conflicts to fix"}
        
        if not self.can_auto_fix:
            return {
                "success": False,
                "message": "Intent conflicts require manual resolution",
                "conflicts": len(self.conflict_details),
                "fix_instructions": self.fix_instructions
            }
        
        # Handle safe auto-fixes
        try:
            conflict = self.conflict_details[0]
            
            if self.fix_type == "configure_web_server_access":
                return self._configure_web_server_fix(client, instance_id)
            else:
                return {
                    "success": False,
                    "message": f"Auto-fix not implemented for {self.fix_type}",
                    "recommendation": "Follow manual fix instructions"
                }
        
        except ClientError as e:
            return {
                "success": False,
                "message": f"Error applying fix: {e}",
                "recommendation": "Manual resolution required"
            }
    
    def _configure_web_server_fix(self, client, instance_id):
        """Configure web server access by opening HTTP/HTTPS ports."""
        # This would implement the actual security group modification
        # For safety, we'll return instructions instead of making changes
        return {
            "success": False,
            "message": "Web server configuration requires manual security group changes",
            "recommendation": "Follow fix instructions to open HTTP/HTTPS ports safely"
        }
