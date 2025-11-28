# agents/ec2_agent/ec2_agent.py

import boto3
import pkgutil
import importlib
import inspect
from pathlib import Path
import yaml
import json
from typing import Dict, List, Optional, Any

from agents.ec2_agent.executor import EC2Executor
from .doc_search import DocSearch
from .llm_fallback import LLMFallback
from .intent_detector import EC2IntentDetector


class EC2Agent:
    def __init__(self, client=None, creds=None):
        if client and hasattr(client, 'describe_instances'):  
            # If explicitly passed a boto3 EC2 client (check it has EC2 methods)
            self.client = client
        elif client and isinstance(client, dict):
            # If first param is actually credentials dict
            self.client = boto3.client(
                "ec2",
                aws_access_key_id=client.get("aws_access_key_id"),
                aws_secret_access_key=client.get("aws_secret_access_key"),
                aws_session_token=client.get("aws_session_token"),
                region_name=client.get("region", "us-east-1"),
            )
        elif creds:  
            # Build boto3 client from creds dict
            self.client = boto3.client(
                "ec2",
                aws_access_key_id=creds.get("aws_access_key_id"),
                aws_secret_access_key=creds.get("aws_secret_access_key"),
                aws_session_token=creds.get("aws_session_token"),
                region_name=creds.get("region", "us-east-1"),
            )
        else:
            # Fallback: default boto3 client (uses local ~/.aws/credentials or env vars)
            self.client = boto3.client("ec2")
            
        # Initialize components
        self.rules = self._load_rules()
        self.doc_search = DocSearch()
        self.llm_fallback = LLMFallback()
        self.intent_detector = EC2IntentDetector()
        self.executor = EC2Executor()

    def _load_rules(self):
        """Dynamically import all rule classes from rules/ directory."""
        rules = []
        rules_path = Path(__file__).parent / "rules"

        for module_info in pkgutil.iter_modules([str(rules_path)]):
            module_name = f"agents.ec2_agent.rules.{module_info.name}"
            module = importlib.import_module(module_name)

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, "check") and hasattr(obj, "fix"):
                    rules.append(obj())
        return rules

    def scan(self, user_intent_input=None, scope="all"):
        """
        Scan EC2 instances for issues using intent-aware rules.
        Returns normalized findings with intent context.
        
        Args:
            user_intent_input: Dict with user's explicit intent per instance
                              e.g., {"i-1234567890": "web_server", "i-0987654321": "database_server"}
            scope: "all", "running", "stopped", specific instance ID, or list of instance IDs
        """
        findings = []
        
        # Determine scan scope
        instances_to_scan = self._get_scan_instances(scope)
        
        if not instances_to_scan:
            print("⚠️ No instances found to scan")
            return self.executor.format_for_fixer([])
        
        # Step 1: Intent-aware rules-based detection
        for instance in instances_to_scan:
            instance_id = instance['InstanceId']
            
            # Detect intent for this instance
            user_intent = None
            if user_intent_input:
                # Check for instance-specific intent first
                user_intent = user_intent_input.get(instance_id)
                # If no instance-specific intent, check for global intent
                if not user_intent:
                    user_intent = user_intent_input.get('_global_intent')
            
            print(f"DEBUG: user_intent for {instance_id} = {user_intent}")
            
            intent, confidence, reasoning = self.intent_detector.detect_intent(
                instance_id, self.client, user_intent
            )
            
            print(f"🎯 Intent for {instance_id}: {intent.value} (confidence: {confidence:.2f})")
            print(f"   Reasoning: {reasoning}")
            
            # Get intent-specific recommendations
            recommendations = self.intent_detector.get_intent_recommendations(intent, instance_id)
            
            # Apply rules with intent context
            for rule in self.rules:
                try:
                    # Pass intent context to rule
                    if hasattr(rule, 'check_with_intent'):
                        # Intent-aware rules
                        if rule.id in ["ec2_intent_conversion"]:
                            rule.intent_confidence = confidence  # Store confidence for auto_safe decision
                        issue_found = rule.check_with_intent(self.client, instance_id, intent, recommendations)
                    else:
                        # Standard rules - pass instance ID and client
                        issue_found = self._call_rule_check(rule, instance_id, instance)
                        
                    if issue_found:
                        # Adjust auto_safe based on intent
                        auto_safe = self._should_auto_apply(rule, intent, instance_id, instance)
                        
                        # Get rule fix information
                        fix_instructions = getattr(rule, 'fix_instructions', None)
                        can_auto_fix = getattr(rule, 'can_auto_fix', False)
                        fix_type = getattr(rule, 'fix_type', None)
                        
                        # DEBUG: Log for instruction details
                        print(f"DEBUG: Rule {rule.id} - fix_instructions: {fix_instructions}")
                        print(f"DEBUG: Rule {rule.id} - can_auto_fix: {can_auto_fix}")
                        print(f"DEBUG: Rule {rule.id} - fix_type: {fix_type}")
                        print(f"DEBUG: Rule {rule.id} - auto_safe: {auto_safe}")
                        
                        finding = {
                            "service": "ec2",
                            "resource": instance_id,
                            "issue": rule.detection,
                            "rule_id": rule.id,
                            "auto_safe": auto_safe,
                            "source": "rule",
                            "intent": intent.value,
                            "intent_confidence": confidence,
                            "intent_reasoning": reasoning,
                            "recommendations": recommendations,
                            "instance_state": instance.get('State', {}).get('Name', 'unknown'),
                            "instance_type": instance.get('InstanceType', 'unknown')
                        }
                        
                        # Add auto-fix action for auto-safe issues
                        if auto_safe:
                            finding["fix"] = self._create_auto_fix_action(rule, instance_id, instance)
                        
                        # Add fix info when available (for both auto and manual fixes)
                        if fix_instructions:
                            print(f"DEBUG: Adding fix instructions to finding for {instance_id}")
                            finding.update({
                                "fix_instructions": fix_instructions,
                                "can_auto_fix": can_auto_fix,
                                "fix_type": fix_type
                            })
                        else:
                            print(f"DEBUG: No fix instructions available for {instance_id}")
                        
                        findings.append(finding)
                        
                except Exception as e:
                    findings.append({
                        "service": "ec2",
                        "resource": instance_id,
                        "issue": f"Error checking rule {rule.id}: {str(e)}",
                        "rule_id": rule.id,
                        "auto_safe": False,
                        "source": "rule_error",
                        "intent": intent.value if 'intent' in locals() else "unknown",
                        "instance_state": instance.get('State', {}).get('Name', 'unknown')
                    })

        # If no rule-based findings, try doc search + LLM with intent context
        if not any(f["source"] == "rule" for f in findings):
            for instance in instances_to_scan[:5]:  # Limit to first 5 for performance
                instance_id = instance['InstanceId']
                
                # Get intent if not already detected
                if not any(f["resource"] == instance_id for f in findings):
                    user_intent = user_intent_input.get(instance_id) if user_intent_input else None
                    intent, confidence, reasoning = self.intent_detector.detect_intent(
                        instance_id, self.client, user_intent
                    )
                
                # Step 2: Intent-aware doc search
                docs = self.doc_search.search(f"EC2 instance {intent.value} misconfiguration", intent.value)
                if docs and isinstance(docs, dict):  # Enhanced docs with intent context
                    findings.append({
                        "service": "ec2",
                        "resource": instance_id,
                        "issue": f"Potential {intent.value} configuration issue",
                        "note": docs,
                        "rule_id": "doc_ref",
                        "auto_safe": False,
                        "source": "doc_search",
                        "intent": intent.value,
                        "intent_confidence": confidence,
                        "instance_state": instance.get('State', {}).get('Name', 'unknown')
                    })
                elif docs:  # Simple string response
                    findings.append({
                        "service": "ec2",
                        "resource": instance_id,
                        "issue": f"Potential {intent.value} configuration issue",
                        "note": docs,
                        "rule_id": "doc_ref",
                        "auto_safe": False,
                        "source": "doc_search",
                        "intent": intent.value,
                        "intent_confidence": confidence,
                        "instance_state": instance.get('State', {}).get('Name', 'unknown')
                    })
                else:
                    # Step 3: Intent-aware LLM fallback
                    llm_fix = self.llm_fallback.suggest_fix(
                        f"EC2 instance {intent.value} configuration issue", 
                        intent.value, 
                        instance_id
                    )
                    findings.append({
                        "service": "ec2",
                        "resource": instance_id,
                        "issue": f"Unknown {intent.value} issue",
                        "fix": llm_fix,
                        "rule_id": "llm_fallback",
                        "auto_safe": False,
                        "source": "llm",
                        "intent": intent.value,
                        "intent_confidence": confidence,
                        "instance_state": instance.get('State', {}).get('Name', 'unknown')
                    })
                    
        # Step 4: Return normalized findings
        return self.executor.format_for_fixer(findings)

    def _get_scan_instances(self, scope):
        """Get instances to scan based on scope."""
        try:
            if scope == "all":
                # Get all instances (running and stopped)
                response = self.client.describe_instances()
                instances = []
                for reservation in response['Reservations']:
                    instances.extend(reservation['Instances'])
                return instances
            
            elif scope == "running":
                # Get only running instances
                response = self.client.describe_instances(
                    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
                )
                instances = []
                for reservation in response['Reservations']:
                    instances.extend(reservation['Instances'])
                return instances
            
            elif scope == "stopped":
                # Get only stopped instances
                response = self.client.describe_instances(
                    Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}]
                )
                instances = []
                for reservation in response['Reservations']:
                    instances.extend(reservation['Instances'])
                return instances
            
            elif isinstance(scope, str) and scope.startswith("i-"):
                # Single instance ID
                response = self.client.describe_instances(InstanceIds=[scope])
                instances = []
                for reservation in response['Reservations']:
                    instances.extend(reservation['Instances'])
                return instances
            
            elif isinstance(scope, list):
                # Multiple instance IDs
                response = self.client.describe_instances(InstanceIds=scope)
                instances = []
                for reservation in response['Reservations']:
                    instances.extend(reservation['Instances'])
                return instances
            
            else:
                print(f"⚠️ Unknown scope: {scope}. Defaulting to running instances.")
                return self._get_scan_instances("running")
                
        except Exception as e:
            print(f"❌ Error getting instances for scope '{scope}': {e}")
            return []

    def _call_rule_check(self, rule, instance_id, instance):
        """Call rule check method with appropriate parameters."""
        try:
            if rule.id == "ec2_open_security_group":
                return rule.check(self.client, instance_id)
            elif rule.id == "ec2_unencrypted_ebs":
                return rule.check(self.client, instance_id)
            elif rule.id == "ec2_missing_backups":
                return rule.check(self.client, instance_id)
            elif rule.id == "ec2_unused_instance":
                return rule.check(self.client, instance_id, instance)
            elif rule.id == "ec2_oversized_instance":
                return rule.check(self.client, instance_id, instance)
            elif rule.id == "ec2_missing_monitoring":
                return rule.check(self.client, instance_id)
            elif rule.id == "ec2_outdated_ami":
                return rule.check(self.client, instance_id, instance)
            elif rule.id == "ec2_public_database":
                return rule.check(self.client, instance_id, instance)
            else:
                # Try generic check method
                return rule.check(self.client, instance_id)
        except Exception as e:
            print(f"⚠️ Error calling rule check for {rule.id}: {e}")
            return False

    def _should_auto_apply(self, rule, intent, instance_id, instance):
        """
        Determine if a rule should be auto-applied based on intent context.
        
        This prevents dangerous auto-fixes like stopping production instances.
        """
        from .intent_detector import EC2Intent
        
        instance_state = instance.get('State', {}).get('Name', 'unknown')
        
        # Intent conversion rule - check confidence for explicit user intent
        if rule.id == "ec2_intent_conversion":
            rule_confidence = getattr(rule, 'intent_confidence', 0.0)
            print(f"DEBUG: Intent conversion rule confidence: {rule_confidence}")
            if rule_confidence >= 1.0:  # Explicit user intent
                print(f"✅ Explicit user intent ({rule_confidence:.2f}) - auto-enabling intent conversion")
                return True
            else:
                print(f"⚠️ Intent conversion detected for {instance_id} - requiring manual review (confidence: {rule_confidence})")
                return False  # Manual review for inferred intent conflicts
        
        # Web server intent - be careful with security changes
        if intent == EC2Intent.WEB_SERVER:
            if rule.id == "ec2_open_security_group":
                # Don't auto-fix security groups for web servers (might break public access)
                print(f"⚠️ Skipping auto-fix for security groups on web server: {instance_id}")
                return False
            elif rule.id == "ec2_missing_monitoring":
                return True  # Safe to enable monitoring
                
        # Database server intent - apply security rules carefully
        elif intent == EC2Intent.DATABASE_SERVER:
            if rule.id == "ec2_public_database":
                return True  # Safe to restrict database public access
            elif rule.id == "ec2_unencrypted_ebs":
                return False  # EBS encryption requires instance restart
            elif rule.id == "ec2_missing_backups":
                return True  # Safe to enable automated backups
                
        # Development/testing intent - allow cost optimizations
        elif intent == EC2Intent.DEVELOPMENT_TESTING:
            if rule.id == "ec2_unused_instance" and instance_state == "stopped":
                return True  # Safe to handle stopped dev instances
            elif rule.id == "ec2_oversized_instance":
                return False  # Instance type changes require restart
            elif rule.id == "ec2_missing_monitoring":
                return True  # Safe to enable monitoring
                
        # Bastion host intent - be very careful with security
        elif intent == EC2Intent.BASTION_HOST:
            if rule.id == "ec2_open_security_group":
                return False  # Manual review required for bastion security changes
            elif rule.id == "ec2_missing_monitoring":
                return True  # Safe to enable monitoring for bastions
                
        # Batch processing intent - allow optimization
        elif intent == EC2Intent.BATCH_PROCESSING:
            if rule.id == "ec2_unused_instance":
                return True  # Safe to optimize batch instances
            elif rule.id == "ec2_missing_monitoring":
                return True  # Safe to enable monitoring
                
        # HPC intent - don't interfere with performance
        elif intent == EC2Intent.HIGH_PERFORMANCE_COMPUTING:
            if rule.id == "ec2_oversized_instance":
                return False  # HPC often needs large instances
            elif rule.id == "ec2_missing_monitoring":
                return True  # Safe to enable monitoring
                
        # For unknown intent, be conservative
        elif intent == EC2Intent.UNKNOWN:
            if rule.id in ["ec2_missing_monitoring", "ec2_missing_backups"]:
                return True  # Generally safe operations
            else:
                return False  # Don't auto-fix if not sure of intent
                
        # Default to rule's original auto_safe setting
        return getattr(rule, 'auto_safe', False)

    def _create_auto_fix_action(self, rule, instance_id, instance):
        """Create auto-fix action based on rule and instance."""
        if rule.id == "ec2_open_security_group":
            return {
                "action": "restrict_security_group",
                "params": {"instance_id": instance_id}
            }
        elif rule.id == "ec2_unencrypted_ebs":
            return {
                "action": "encrypt_ebs_volume", 
                "params": {"instance_id": instance_id}
            }
        elif rule.id == "ec2_missing_backups":
            return {
                "action": "create_ebs_snapshots",
                "params": {"instance_id": instance_id}
            }
        elif rule.id == "ec2_unused_instance":
            return {
                "action": "stop_unused_instance",
                "params": {"instance_id": instance_id}
            }
        elif rule.id == "ec2_missing_monitoring":
            return {
                "action": "enable_cloudwatch_monitoring",
                "params": {"instance_id": instance_id}
            }
        elif rule.id == "ec2_public_database":
            return {
                "action": "restrict_database_access",
                "params": {"instance_id": instance_id}
            }
        else:
            # Generic fix - let the rule handle it
            return {
                "action": "rule_based_fix",
                "params": {"rule_id": rule.id, "instance_id": instance_id}
            }

    def apply_fix(self, finding):
        """
        Apply fix if auto_safe is True, else recommend manual review.
        """
        for rule in self.rules:
            if rule.id == finding.get("rule_id"):
                if finding.get("auto_safe"):
                    try:
                        # Call rule fix with appropriate parameters
                        result = self._call_rule_fix(rule, finding)
                        if isinstance(result, dict) and result.get('success'):
                            return f"✅ Applied fix for {rule.id} on {finding['resource']}"
                        else:
                            error_msg = result.get('message', 'Unknown error') if isinstance(result, dict) else str(result)
                            return f"❌ Failed to fix {rule.id} on {finding['resource']}: {error_msg}"
                    except Exception as e:
                        return f"❌ Failed to fix {rule.id} on {finding['resource']}: {str(e)}"
                else:
                    return f"⚠️ Fix for {rule.id} requires manual approval"
        return "⚠️ Rule not found or handled by doc/LLM"

    def _call_rule_fix(self, rule, finding):
        """Call rule fix method with appropriate parameters."""
        instance_id = finding['resource']
        
        try:
            if rule.id == "ec2_open_security_group":
                return rule.fix(self.client, instance_id)
            elif rule.id == "ec2_unencrypted_ebs":
                return rule.fix(self.client, instance_id)
            elif rule.id == "ec2_missing_backups":
                return rule.fix(self.client, instance_id)
            elif rule.id == "ec2_unused_instance":
                return rule.fix(self.client, instance_id, auto_approve=True)
            elif rule.id == "ec2_missing_monitoring":
                return rule.fix(self.client, instance_id)
            elif rule.id == "ec2_intent_conversion":
                return rule.fix(self.client, instance_id)
            else:
                # Try generic fix method
                return rule.fix(self.client, instance_id)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_scan_summary(self, findings):
        """Get a summary of scan results."""
        summary = {
            "total_findings": len(findings),
            "auto_fixable": len([f for f in findings if f.get("auto_safe")]),
            "manual_review": len([f for f in findings if not f.get("auto_safe")]),
            "by_intent": {},
            "by_instance_state": {},
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0}
        }
        
        for finding in findings:
            # Count by intent
            intent = finding.get("intent", "unknown")
            summary["by_intent"][intent] = summary["by_intent"].get(intent, 0) + 1
            
            # Count by instance state
            state = finding.get("instance_state", "unknown")
            summary["by_instance_state"][state] = summary["by_instance_state"].get(state, 0) + 1
            
            # Count by severity (based on rule priority)
            rule_id = finding.get("rule_id", "")
            severity = self._get_rule_severity(rule_id)
            summary["by_severity"][severity] += 1
        
        return summary

    def _get_rule_severity(self, rule_id):
        """Get severity level for a rule."""
        critical_rules = ["ec2_open_security_group", "ec2_public_database", "ec2_unencrypted_ebs"]
        high_rules = ["ec2_missing_backups", "ec2_outdated_ami", "ec2_missing_monitoring"]
        medium_rules = ["ec2_oversized_instance", "ec2_unused_instance", "ec2_intent_conversion"]
        
        if rule_id in critical_rules:
            return "critical"
        elif rule_id in high_rules:
            return "high"
        elif rule_id in medium_rules:
            return "medium"
        else:
            return "low"

    def get_cost_optimization_summary(self, findings):
        """Get cost optimization opportunities from findings."""
        cost_savings = {
            "total_potential_monthly_savings": 0,
            "optimization_opportunities": [],
            "quick_wins": [],
            "long_term_optimizations": []
        }
        
        for finding in findings:
            rule_id = finding.get("rule_id", "")
            instance_id = finding["resource"]
            intent = finding.get("intent", "")
            
            if rule_id == "ec2_unused_instance":
                cost_savings["optimization_opportunities"].append({
                    "type": "Stop unused instance",
                    "instance": instance_id,
                    "estimated_monthly_savings": "$50-200",
                    "effort": "Low"
                })
                cost_savings["quick_wins"].append(f"Stop instance {instance_id}")
                
            elif rule_id == "ec2_oversized_instance":
                cost_savings["optimization_opportunities"].append({
                    "type": "Right-size instance",
                    "instance": instance_id,
                    "estimated_monthly_savings": "$20-100",
                    "effort": "Medium"
                })
                cost_savings["long_term_optimizations"].append(f"Right-size instance {instance_id}")
                
            elif intent == "development_testing":
                cost_savings["optimization_opportunities"].append({
                    "type": "Use Spot instances or scheduling",
                    "instance": instance_id,
                    "estimated_monthly_savings": "$30-150",
                    "effort": "Medium"
                })
        
        return cost_savings
