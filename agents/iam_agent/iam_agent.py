# agents/iam_agent/iam_agent.py

import boto3
import pkgutil
import importlib
import inspect
from pathlib import Path
import yaml
import json
from typing import Dict, List, Optional, Any

from agents.iam_agent.executor import IAMExecutor
from agents.utils.llm_security_analyzer import LLMSecurityAnalyzer
from agents.utils.rag_security_search import RAGSecuritySearch
from .doc_search import DocSearch
from .llm_fallback import LLMFallback
from .intent_detector import IAMIntentDetector


class IAMAgent:
    def __init__(self, client=None, creds=None):
        if client and hasattr(client, 'list_users'):  
            # If explicitly passed a boto3 IAM client (check it has IAM methods)
            self.client = client
        elif client and isinstance(client, dict):
            # If first param is actually credentials dict
            self.client = boto3.client(
                "iam",
                aws_access_key_id=client.get("aws_access_key_id"),
                aws_secret_access_key=client.get("aws_secret_access_key"),
                aws_session_token=client.get("aws_session_token"),
                region_name=client.get("region", "us-east-1"),
            )
        elif creds:  
            # Build boto3 client from creds dict
            self.client = boto3.client(
                "iam",
                aws_access_key_id=creds.get("aws_access_key_id"),
                aws_secret_access_key=creds.get("aws_secret_access_key"),
                aws_session_token=creds.get("aws_session_token"),
                region_name=creds.get("region", "us-east-1"),
            )
        else:
            # Fallback: default boto3 client (uses local ~/.aws/credentials or env vars)
            self.client = boto3.client("iam")
            
        # Initialize components
        self.rules = self._load_rules()
        self.doc_search = DocSearch()
        self.llm_fallback = LLMFallback()
        self.intent_detector = IAMIntentDetector()
        self.executor = IAMExecutor()
        
        # Initialize new detection tiers
        self.rag_search = RAGSecuritySearch()
        self.llm_analyzer = None
        
        # Initialize LLM only if API key exists
        try:
            self.llm_analyzer = LLMSecurityAnalyzer()
            print("[IAMAgent] ✅ LLM fallback enabled (Gemini)")
        except ValueError as e:
            print(f"[IAMAgent] ⚠️  LLM fallback disabled: {e}")

    def _load_rules(self):
        """Dynamically import all rule classes from rules/ directory."""
        rules = []
        rules_path = Path(__file__).parent / "rules"

        for module_info in pkgutil.iter_modules([str(rules_path)]):
            module_name = f"agents.iam_agent.rules.{module_info.name}"
            module = importlib.import_module(module_name)

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, "check") and hasattr(obj, "fix"):
                    rules.append(obj())
        return rules

    def scan(self, user_intent_input=None, scope="account"):
        """
        Scan IAM resources for issues using intent-aware rules.
        Returns normalized findings with intent context.
        
        Args:
            user_intent_input: Dict with user's explicit intent per resource
                              e.g., {"user1": "least_privilege", "role1": "service_role"}
            scope: "account", "users", "roles", "policies", or specific resource name
        """
        findings = []
        
        # Determine scan scope
        resources_to_scan = self._get_scan_resources(scope)
        
        # Step 1: Intent-aware rules-based detection
        for resource_type, resource_list in resources_to_scan.items():
            for resource in resource_list:
                resource_name = self._get_resource_name(resource_type, resource)
                
                # Detect intent for this resource
                user_intent = None
                if user_intent_input:
                    # Check for resource-specific intent first
                    user_intent = user_intent_input.get(resource_name)
                    # If no resource-specific intent, check for global intent
                    if not user_intent:
                        user_intent = user_intent_input.get('_global_intent')
                
                print(f"DEBUG: user_intent for {resource_name} ({resource_type}) = {user_intent}")
                
                intent, confidence, reasoning = self.intent_detector.detect_intent(
                    resource_type, resource_name, self.client, user_intent
                )
                
                print(f"🎯 Intent for {resource_name} ({resource_type}): {intent.value} (confidence: {confidence:.2f})")
                print(f"   Reasoning: {reasoning}")
                
                # Get intent-specific recommendations
                recommendations = self.intent_detector.get_intent_recommendations(intent, resource_type, resource_name)
                
                # Apply rules with intent context
                for rule in self.rules:
                    try:
                        # Pass intent context to rule
                        if hasattr(rule, 'check_with_intent'):
                            # Intent-aware rules
                            if rule.id in ["iam_intent_conversion"]:
                                rule.intent_confidence = confidence  # Store confidence for auto_safe decision
                            issue_found = rule.check_with_intent(self.client, resource_type, resource_name, intent, recommendations)
                        else:
                            # Standard rules - pass appropriate parameters
                            issue_found = self._call_rule_check(rule, resource_type, resource_name)
                            
                        if issue_found:
                            # Adjust auto_safe based on intent
                            auto_safe = self._should_auto_apply(rule, intent, resource_type, resource_name)
                            
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
                                "service": "iam",
                                "resource": resource_name,
                                "resource_type": resource_type,
                                "issue": rule.detection,
                                "rule_id": rule.id,
                                "auto_safe": auto_safe,
                                "source": "rule",
                                "intent": intent.value,
                                "intent_confidence": confidence,
                                "intent_reasoning": reasoning,
                                "recommendations": recommendations
                            }
                            
                            # Add auto-fix action for auto-safe issues
                            if auto_safe:
                                finding["fix"] = self._create_auto_fix_action(rule, resource_type, resource_name)
                            
                            # Add fix info when available (for both auto and manual fixes)
                            if fix_instructions:
                                print(f"DEBUG: Adding fix instructions to finding for {resource_name}")
                                finding.update({
                                    "fix_instructions": fix_instructions,
                                    "can_auto_fix": can_auto_fix,
                                    "fix_type": fix_type
                                })
                            else:
                                print(f"DEBUG: No fix instructions available for {resource_name}")
                            
                            findings.append(finding)
                            
                    except Exception as e:
                        findings.append({
                            "service": "iam",
                            "resource": resource_name,
                            "resource_type": resource_type,
                            "issue": f"Error checking rule {rule.id}: {str(e)}",
                            "rule_id": rule.id,
                            "auto_safe": False,
                            "source": "rule_error",
                            "intent": intent.value if 'intent' in locals() else "unknown"
                        })

        # If no rule-based findings, try doc search + LLM with intent context
        if not any(f["source"] == "rule" for f in findings):
            for resource_type, resource_list in resources_to_scan.items():
                for resource in resource_list[:5]:  # Limit to first 5 for performance
                    resource_name = self._get_resource_name(resource_type, resource)
                    
                    # Get intent if not already detected
                    if not any(f["resource"] == resource_name for f in findings):
                        user_intent = user_intent_input.get(resource_name) if user_intent_input else None
                        intent, confidence, reasoning = self.intent_detector.detect_intent(
                            resource_type, resource_name, self.client, user_intent
                        )
                    
                    # Step 2: Intent-aware doc search
                    docs = self.doc_search.search(f"IAM {resource_type} {intent.value} misconfiguration", intent.value)
                    if docs and isinstance(docs, dict):  # Enhanced docs with intent context
                        findings.append({
                            "service": "iam",
                            "resource": resource_name,
                            "resource_type": resource_type,
                            "issue": f"Potential {intent.value} configuration issue",
                            "note": docs,
                            "rule_id": "doc_ref",
                            "auto_safe": False,
                            "source": "doc_search",
                            "intent": intent.value,
                            "intent_confidence": confidence
                        })
                    elif docs:  # Simple string response
                        findings.append({
                            "service": "iam",
                            "resource": resource_name,
                            "resource_type": resource_type,
                            "issue": f"Potential {intent.value} configuration issue",
                            "note": docs,
                            "rule_id": "doc_ref",
                            "auto_safe": False,
                            "source": "doc_search",
                            "intent": intent.value,
                            "intent_confidence": confidence
                        })
                    else:
                        # Step 3: Intent-aware LLM fallback
                        llm_fix = self.llm_fallback.suggest_fix(
                            f"IAM {resource_type} {intent.value} configuration issue", 
                            intent.value, 
                            resource_name
                        )
                        findings.append({
                            "service": "iam",
                            "resource": resource_name,
                            "resource_type": resource_type,
                            "issue": f"Unknown {intent.value} issue",
                            "fix": llm_fix,
                            "rule_id": "llm_fallback",
                            "auto_safe": False,
                            "source": "llm",
                            "intent": intent.value,
                            "intent_confidence": confidence
                        })
        
        # Count rule findings
        rule_findings_count = sum(1 for f in findings if f.get("source") == "rule")
        print(f"\n[IAMAgent] TIER 1 (Rules): Found {rule_findings_count} total issues")
        
        # TIER 2: RAG-based detection
        print(f"\n[IAMAgent] TIER 2 (RAG): Starting knowledge base search...")
        for resource_type, resource_list in resources_to_scan.items():
            for resource in resource_list:
                resource_name = self._get_resource_name(resource_type, resource)
                user_intent = user_intent_input.get(resource_name) if user_intent_input else None
                if not user_intent and user_intent_input:
                    user_intent = user_intent_input.get('_global_intent')
                
                intent, confidence, reasoning = self.intent_detector.detect_intent(resource_type, resource_name, self.client, user_intent)
                resource_config = self._get_resource_config(resource_type, resource_name)
                
                rag_findings = self.rag_search.search_security_issues(
                    service='iam', configuration=resource_config, intent=intent.value, top_k=5
                )
                
                for rag_finding in rag_findings:
                    rag_finding.update({'resource': resource_name, 'service': 'iam', 'source': 'rag', 'tier': 2,
                                       'intent': intent.value, 'intent_confidence': confidence, 'resource_type': resource_type})
                    findings.append(rag_finding)
        
        rag_findings_count = sum(1 for f in findings if f.get("source") == "rag")
        print(f"[IAMAgent] TIER 2 (RAG): Found {rag_findings_count} additional issues")
        
        # TIER 3: LLM fallback
        if self.llm_analyzer:
            print(f"\n[IAMAgent] TIER 3 (LLM): Starting Gemini analysis...")
            llm_findings_count = 0
            for resource_type, resource_list in resources_to_scan.items():
                for resource in resource_list:
                    resource_name = self._get_resource_name(resource_type, resource)
                    resource_findings = [f for f in findings if f.get("resource") == resource_name]
                    
                    if len(resource_findings) < 3:
                        user_intent = user_intent_input.get(resource_name) if user_intent_input else None
                        if not user_intent and user_intent_input:
                            user_intent = user_intent_input.get('_global_intent')
                        
                        intent, confidence, reasoning = self.intent_detector.detect_intent(resource_type, resource_name, self.client, user_intent)
                        resource_config = self._get_resource_config(resource_type, resource_name)
                        
                        llm_findings = self.llm_analyzer.analyze_security_issues(
                            service='iam', resource_name=resource_name, configuration=resource_config,
                            intent=intent.value, user_context=str(user_intent_input) if user_intent_input else ""
                        )
                        
                        for llm_finding in llm_findings:
                            llm_finding.update({'service': 'iam', 'source': 'llm', 'tier': 3, 'resource_type': resource_type,
                                               'intent': intent.value, 'intent_confidence': confidence, 'rule_id': 'llm_fallback'})
                            findings.append(llm_finding)
                            llm_findings_count += 1
            
            print(f"[IAMAgent] TIER 3 (LLM): Found {llm_findings_count} additional issues")
        else:
            print(f"[IAMAgent] TIER 3 (LLM): Skipped - Gemini API not configured")
        
        # Deduplicate
        findings = self._deduplicate_findings(findings)
        print(f"\n[IAMAgent] Analysis Complete: {len(findings)} unique findings\n")
                        
        # Step 4: Return normalized findings
        return self.executor.format_for_fixer(findings)

    def _get_scan_resources(self, scope):
        """Get resources to scan based on scope."""
        resources = {}
        
        try:
            if scope == "account" or scope == "users":
                users = self.client.list_users().get('Users', [])[:50]  # Limit for performance
                resources['user'] = users
                
            if scope == "account" or scope == "roles":
                roles = self.client.list_roles().get('Roles', [])[:50]  # Limit for performance
                # Filter out AWS service roles to focus on customer roles
                customer_roles = [r for r in roles if not r['RoleName'].startswith('aws-')]
                resources['role'] = customer_roles
                
            if scope == "account" or scope == "policies":
                policies = self.client.list_policies(Scope='Local').get('Policies', [])[:30]  # Customer managed only
                resources['policy'] = policies
                
            # Handle specific resource name
            if scope not in ["account", "users", "roles", "policies"]:
                # Try to find specific resource
                try:
                    user = self.client.get_user(UserName=scope)
                    resources['user'] = [user['User']]
                except:
                    try:
                        role = self.client.get_role(RoleName=scope)
                        resources['role'] = [role['Role']]
                    except:
                        try:
                            # Try as policy ARN or name
                            if scope.startswith('arn:'):
                                policy = self.client.get_policy(PolicyArn=scope)
                                resources['policy'] = [policy['Policy']]
                            else:
                                # Search for policy by name
                                policies = self.client.list_policies(Scope='Local').get('Policies', [])
                                matching_policy = [p for p in policies if p['PolicyName'] == scope]
                                if matching_policy:
                                    resources['policy'] = matching_policy
                        except:
                            print(f"⚠️ Resource '{scope}' not found")
                            
        except Exception as e:
            print(f"❌ Error getting scan resources: {e}")
            
        return resources

    def _get_resource_name(self, resource_type, resource):
        """Extract resource name from resource object."""
        if resource_type == "user":
            return resource.get('UserName', 'unknown')
        elif resource_type == "role":
            return resource.get('RoleName', 'unknown')
        elif resource_type == "policy":
            return resource.get('PolicyName', 'unknown')
        else:
            return str(resource)

    def _call_rule_check(self, rule, resource_type, resource_name):
        """Call rule check method with appropriate parameters."""
        try:
            if rule.id == "iam_mfa_enforcement":
                return rule.check(self.client, resource_name)
            elif rule.id == "iam_least_privilege":
                return rule.check(self.client, resource_type, resource_name)
            elif rule.id == "iam_access_key_rotation":
                if resource_type == "user":
                    return rule.check(self.client, resource_name)
                else:
                    return False  # Only applies to users
            elif rule.id == "iam_inactive_user":
                if resource_type == "user":
                    return rule.check(self.client, resource_name)
                else:
                    return False  # Only applies to users
            else:
                # Try generic check method
                return rule.check(self.client, resource_type, resource_name)
        except Exception as e:
            print(f"⚠️ Error calling rule check for {rule.id}: {e}")
            return False

    def _should_auto_apply(self, rule, intent, resource_type, resource_name):
        """
        Determine if a rule should be auto-applied based on intent context.
        
        This prevents dangerous auto-fixes like removing admin access for service accounts.
        """
        from .intent_detector import IAMIntent
        
        # Intent conversion rule - check confidence for explicit user intent
        if rule.id == "iam_intent_conversion":
            rule_confidence = getattr(rule, 'intent_confidence', 0.0)
            print(f"DEBUG: Intent conversion rule confidence: {rule_confidence}")
            if rule_confidence >= 1.0:  # Explicit user intent
                print(f"✅ Explicit user intent ({rule_confidence:.2f}) - auto-enabling intent conversion")
                return True
            else:
                print(f"⚠️ Intent conversion detected for {resource_name} - requiring manual review (confidence: {rule_confidence})")
                return False  # Manual review for inferred intent conflicts
        
        # Least privilege intent - be careful with permission reduction
        if intent == IAMIntent.LEAST_PRIVILEGE:
            if rule.id == "iam_least_privilege":
                # Only auto-fix low-risk violations
                risk_score = getattr(rule, 'risk_score', 50)
                if risk_score < 20:  # Low risk
                    return True
                else:
                    print(f"⚠️ High-risk privilege violations detected - requiring manual review")
                    return False
            elif rule.id == "iam_mfa_enforcement":
                return True  # Safe to auto-enforce MFA for least privilege intent
                
        # Strong security intent - apply security rules
        elif intent == IAMIntent.STRONG_SECURITY:
            if rule.id in ["iam_mfa_enforcement", "iam_access_key_rotation"]:
                return True  # Auto-apply security rules
            elif rule.id == "iam_least_privilege":
                # Be cautious with permission changes
                return False
                
        # Service account intent - be very careful
        elif intent == IAMIntent.SERVICE_ACCOUNT:
            if rule.id == "iam_mfa_enforcement":
                return False  # Service accounts typically don't need MFA
            elif rule.id == "iam_inactive_user":
                return False  # Service accounts may appear inactive but be used programmatically
                
        # Developer flexibility - don't restrict too much
        elif intent == IAMIntent.DEVELOPER_FLEXIBILITY:
            if rule.id == "iam_least_privilege":
                return False  # Don't auto-restrict developer permissions
            elif rule.id == "iam_mfa_enforcement":
                return True   # Still enforce MFA for developers
                
        # Compliance intent - apply all security rules
        elif intent == IAMIntent.COMPLIANCE:
            if rule.id in ["iam_mfa_enforcement", "iam_access_key_rotation", "iam_inactive_user"]:
                return True
            elif rule.id == "iam_least_privilege":
                return False  # Manual review for compliance
                
        # For unknown intent, be conservative
        elif intent == IAMIntent.UNKNOWN:
            if rule.id in ["iam_mfa_enforcement", "iam_access_key_rotation"]:
                return False  # Don't auto-fix if not sure of intent
                
        # Default to rule's original auto_safe setting
        return getattr(rule, 'auto_safe', False)

    def _create_auto_fix_action(self, rule, resource_type, resource_name):
        """Create auto-fix action based on rule and resource."""
        if rule.id == "iam_mfa_enforcement":
            return {
                "action": "enforce_mfa",
                "params": {"user_name": resource_name}
            }
        elif rule.id == "iam_access_key_rotation":
            return {
                "action": "deactivate_unused_keys", 
                "params": {"user_name": resource_name}
            }
        elif rule.id == "iam_inactive_user":
            return {
                "action": "disable_inactive_user",
                "params": {"user_name": resource_name}
            }
        elif rule.id == "iam_least_privilege":
            return {
                "action": "add_mfa_conditions",
                "params": {"resource_type": resource_type, "resource_name": resource_name}
            }
        else:
            # Generic fix - let the rule handle it
            return {
                "action": "rule_based_fix",
                "params": {"rule_id": rule.id, "resource_type": resource_type, "resource_name": resource_name}
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
        resource_name = finding['resource']
        resource_type = finding.get('resource_type', 'user')
        
        try:
            if rule.id == "iam_mfa_enforcement":
                return rule.fix(self.client, resource_name)
            elif rule.id == "iam_least_privilege":
                return rule.fix(self.client, resource_type, resource_name)
            elif rule.id == "iam_access_key_rotation":
                return rule.fix(self.client, auto_approve=True)
            elif rule.id == "iam_inactive_user":
                return rule.fix(self.client, fix_option="disable", auto_approve=True)
            elif rule.id == "iam_intent_conversion":
                return rule.fix(self.client, resource_type, resource_name)
            else:
                # Try generic fix method
                return rule.fix(self.client, resource_name)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_scan_summary(self, findings):
        """Get a summary of scan results."""
        summary = {
            "total_findings": len(findings),
            "auto_fixable": len([f for f in findings if f.get("auto_safe")]),
            "manual_review": len([f for f in findings if not f.get("auto_safe")]),
            "by_resource_type": {},
            "by_intent": {},
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0}
        }
        
        for finding in findings:
            # Count by resource type
            resource_type = finding.get("resource_type", "unknown")
            summary["by_resource_type"][resource_type] = summary["by_resource_type"].get(resource_type, 0) + 1
            
            # Count by intent
            intent = finding.get("intent", "unknown")
            summary["by_intent"][intent] = summary["by_intent"].get(intent, 0) + 1
            
            # Count by severity (if available in rule)
            severity = finding.get("severity", "medium")
            if severity in summary["by_severity"]:
                summary["by_severity"][severity] += 1
        
        return summary

    def _get_resource_config(self, resource_type: str, resource_name: str) -> dict:
        """Collect comprehensive resource configuration for analysis"""
        config = {'resource_type': resource_type, 'resource_name': resource_name}
        
        try:
            if resource_type == 'user':
                config['user'] = self.client.get_user(UserName=resource_name)
                config['policies'] = self.client.list_attached_user_policies(UserName=resource_name).get('AttachedPolicies', [])
                config['groups'] = self.client.list_groups_for_user(UserName=resource_name).get('Groups', [])
                config['access_keys'] = self.client.list_access_keys(UserName=resource_name).get('AccessKeyMetadata', [])
                try:
                    config['mfa_devices'] = self.client.list_mfa_devices(UserName=resource_name).get('MFADevices', [])
                except:
                    config['mfa_devices'] = []
            elif resource_type == 'role':
                config['role'] = self.client.get_role(RoleName=resource_name)
                config['policies'] = self.client.list_attached_role_policies(RoleName=resource_name).get('AttachedPolicies', [])
            elif resource_type == 'policy':
                config['policy'] = self.client.get_policy(PolicyArn=resource_name)
                config['policy_version'] = self.client.get_policy_version(
                    PolicyArn=resource_name,
                    VersionId=config['policy']['Policy']['DefaultVersionId']
                )
        except Exception as e:
            print(f"Error getting config for {resource_type} {resource_name}: {e}")
        
        return config

    def _deduplicate_findings(self, findings: list) -> list:
        """Remove duplicate findings across detection tiers (prefer rules > rag > llm)"""
        seen = {}
        unique = []
        
        for finding in sorted(findings, key=lambda x: x.get('tier', 0)):
            resource = finding.get('resource', '')
            issue = finding.get('issue', '').lower().strip()
            key = (resource, issue)
            
            if key not in seen:
                seen[key] = True
                unique.append(finding)
            else:
                source = finding.get('source', 'unknown')
                print(f"[IAMAgent] Dedup: Skipping duplicate from {source} - {issue}")
        
        return unique
