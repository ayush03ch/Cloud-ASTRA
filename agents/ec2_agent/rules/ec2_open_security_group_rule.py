# agents/ec2_agent/rules/open_security_group_rule.py

import boto3
from botocore.exceptions import ClientError


class OpenSecurityGroupRule:
    """
    Rule to detect EC2 instances with overly permissive security groups
    (allowing access from 0.0.0.0/0 or ::/0).
    """
    
    id = "ec2_open_security_group"
    detection = "EC2 instance has overly permissive security groups"
    auto_safe = False  # Security changes require manual review
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = False
        self.fix_type = None
        self.open_rules = None
    
    def check(self, client, instance_id):
        """Check for overly permissive security group rules."""
        try:
            # Get instance details
            response = client.describe_instances(InstanceIds=[instance_id])
            if not response['Reservations']:
                return False
            
            instance = response['Reservations'][0]['Instances'][0]
            security_groups = instance.get('SecurityGroups', [])
            
            if not security_groups:
                return False
            
            # Get security group details
            sg_ids = [sg['GroupId'] for sg in security_groups]
            sg_response = client.describe_security_groups(GroupIds=sg_ids)
            
            open_rules = []
            for sg in sg_response['SecurityGroups']:
                for rule in sg.get('IpPermissions', []):
                    # Check for overly permissive rules
                    for ip_range in rule.get('IpRanges', []):
                        if ip_range.get('CidrIp') == '0.0.0.0/0':
                            open_rules.append({
                                'sg_id': sg['GroupId'],
                                'sg_name': sg.get('GroupName', 'Unknown'),
                                'protocol': rule.get('IpProtocol', 'Unknown'),
                                'from_port': rule.get('FromPort'),
                                'to_port': rule.get('ToPort'),
                                'cidr': '0.0.0.0/0'
                            })
                    
                    # Check IPv6 ranges
                    for ipv6_range in rule.get('Ipv6Ranges', []):
                        if ipv6_range.get('CidrIpv6') == '::/0':
                            open_rules.append({
                                'sg_id': sg['GroupId'],
                                'sg_name': sg.get('GroupName', 'Unknown'),
                                'protocol': rule.get('IpProtocol', 'Unknown'),
                                'from_port': rule.get('FromPort'),
                                'to_port': rule.get('ToPort'),
                                'cidr': '::/0'
                            })
            
            if open_rules:
                self.open_rules = open_rules
                self._set_fix_instructions(open_rules, instance_id)
                print(f"🔴 Found {len(open_rules)} overly permissive security group rules for {instance_id}")
                return True
            
            return False
            
        except ClientError as e:
            print(f"❌ Error checking security groups for {instance_id}: {e}")
            return False
    
    def _set_fix_instructions(self, open_rules, instance_id):
        """Set instructions for fixing open security groups."""
        self.fix_instructions = [
            f"🔒 Overly Permissive Security Groups for {instance_id}",
            f"Found {len(open_rules)} rules allowing unrestricted access:",
            ""
        ]
        
        for rule in open_rules:
            port_info = f"Port {rule['from_port']}" if rule['from_port'] == rule['to_port'] else f"Ports {rule['from_port']}-{rule['to_port']}"
            if rule['from_port'] is None:
                port_info = "All ports"
            
            self.fix_instructions.extend([
                f"• Security Group: {rule['sg_name']} ({rule['sg_id']})",
                f"  Protocol: {rule['protocol']}, {port_info}",
                f"  Source: {rule['cidr']} (allows access from anywhere)"
            ])
        
        self.fix_instructions.extend([
            "🔧 Remediation Steps:",
            "1. Navigate to EC2 > Security Groups",
            "2. Select the security group with open rules",
            "3. Click 'Edit inbound rules'",
            "4. Replace 0.0.0.0/0 with specific IP ranges or security groups",
            "5. For web servers, consider using a load balancer",
            "6. Test connectivity after changes",
            "⚠️ Impact: May affect application accessibility"
        ])
        
        self.can_auto_fix = False  # Too risky for auto-fix
        self.fix_type = "restrict_security_group_rules"
    
    def check_with_intent(self, client, instance_id, intent, recommendations):
        """Check with intent context - some intents need public access."""
        # First do the standard check
        has_open_rules = self.check(client, instance_id)
        
        if not has_open_rules:
            return False
        
        # Adjust severity based on intent
        from agents.ec2_agent.intent_detector import EC2Intent
        
        if intent == EC2Intent.WEB_SERVER:
            # Web servers might legitimately need HTTP/HTTPS open
            legitimate_ports = [80, 443, 8080, 8443]
            risky_rules = []
            
            for rule in self.open_rules:
                if rule['from_port'] not in legitimate_ports:
                    risky_rules.append(rule)
            
            if risky_rules:
                self.open_rules = risky_rules
                self._set_fix_instructions(risky_rules, instance_id)
                return True
            else:
                # Only web ports are open - this might be acceptable
                print(f"ℹ️ Web server {instance_id} has only HTTP/HTTPS ports open - may be acceptable")
                return False
        
        elif intent == EC2Intent.BASTION_HOST:
            # Bastion hosts might need SSH open but should be restricted
            ssh_rules = [rule for rule in self.open_rules if rule['from_port'] == 22]
            if ssh_rules:
                self.detection = "Bastion host has unrestricted SSH access"
                self._set_fix_instructions(ssh_rules, instance_id)
                return True
        
        return True
    
    def fix(self, client, instance_id):
        """Fix open security groups - requires manual intervention."""
        return {
            "success": False,
            "message": "Security group changes require manual review and approval",
            "affected_rules": len(self.open_rules) if self.open_rules else 0,
            "recommendation": "Follow the fix instructions to manually restrict security group access"
        }
