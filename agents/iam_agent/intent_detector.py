# agents/iam_agent/intent_detector.py

import re
import json
from typing import Dict, List, Optional, Tuple
from enum import Enum


class IAMIntent(Enum):
    """Possible user intents for IAM resources."""
    LEAST_PRIVILEGE = "least_privilege"
    STRONG_SECURITY = "strong_security"
    SERVICE_ACCOUNT = "service_account"
    DEVELOPER_FLEXIBILITY = "developer_flexibility"
    COMPLIANCE = "compliance"
    ADMIN_ACCESS = "admin_access"
    OPERATIONAL_EFFICIENCY = "operational_efficiency"
    AUTOMATION_ROLE = "automation_role"
    UNKNOWN = "unknown"


class IAMIntentDetector:
    """
    Detects user intent for IAM resources through multiple methods:
    1. Explicit user input
    2. Automatic detection based on resource analysis
    3. LLM-powered intent inference
    """
    
    def __init__(self):
        self.service_account_indicators = [
            'service', 'app', 'application', 'system', 'api', 'lambda', 
            'ec2', 'ecs', 'batch', 'glue', 'emr', 'codebuild'
        ]
        
        self.admin_indicators = [
            'admin', 'administrator', 'root', 'superuser', 'master'
        ]
        
        self.developer_indicators = [
            'dev', 'developer', 'development', 'staging', 'test', 'sandbox'
        ]
        
        self.automation_indicators = [
            'automation', 'deploy', 'deployment', 'ci', 'cd', 'pipeline', 
            'jenkins', 'github', 'gitlab', 'terraform', 'ansible'
        ]
        
        self.compliance_indicators = [
            'audit', 'compliance', 'security', 'readonly', 'monitor', 'logging'
        ]

    def detect_intent(self, 
                     resource_type: str,
                     resource_name: str, 
                     client, 
                     user_intent: Optional[str] = None,
                     user_description: Optional[str] = None) -> Tuple[IAMIntent, float, str]:
        """
        Main intent detection method.
        
        Args:
            resource_type: Type of IAM resource (user, role, policy)
            resource_name: Name of the IAM resource
            client: IAM client for API calls
            user_intent: Explicit user intent if provided
            user_description: User's description of resource purpose
            
        Returns:
            Tuple of (Intent, Confidence 0-1, Reasoning)
        """
        print(f"🔍 Detecting intent for {resource_type}: {resource_name}")
        
        # DEBUG: Show what user intent was received
        print(f"DEBUG: user_intent parameter = {user_intent}")
        
        # Priority 1: Explicit user intent
        if user_intent:
            intent = self._parse_user_intent(user_intent)
            print(f"DEBUG: Parsed user intent: {intent} (from '{user_intent}')")
            if intent != IAMIntent.UNKNOWN:
                print(f"✅ User specified intent: {intent.value}")
                return intent, 1.0, "Explicitly specified by user"
        
        # Priority 2: User description analysis
        if user_description:
            intent, confidence, reasoning = self._analyze_user_description(user_description)
            if confidence > 0.7:
                print(f"📝 Intent from description: {intent.value} (confidence: {confidence})")
                return intent, confidence, reasoning
        
        # Priority 3: Automatic detection
        auto_intent, auto_confidence, auto_reasoning = self._auto_detect_intent(resource_type, resource_name, client)
        print(f"🤖 Auto-detected intent: {auto_intent.value} (confidence: {auto_confidence})")
        
        return auto_intent, auto_confidence, auto_reasoning

    def _parse_user_intent(self, user_intent: str) -> IAMIntent:
        """Parse explicit user intent input."""
        intent_mapping = {
            'least privilege': IAMIntent.LEAST_PRIVILEGE,
            'least_privilege': IAMIntent.LEAST_PRIVILEGE,
            'minimal': IAMIntent.LEAST_PRIVILEGE,
            'security': IAMIntent.STRONG_SECURITY,
            'strong security': IAMIntent.STRONG_SECURITY,
            'secure': IAMIntent.STRONG_SECURITY,
            'service': IAMIntent.SERVICE_ACCOUNT,
            'service account': IAMIntent.SERVICE_ACCOUNT,
            'application': IAMIntent.SERVICE_ACCOUNT,
            'developer': IAMIntent.DEVELOPER_FLEXIBILITY,
            'development': IAMIntent.DEVELOPER_FLEXIBILITY,
            'dev': IAMIntent.DEVELOPER_FLEXIBILITY,
            'compliance': IAMIntent.COMPLIANCE,
            'audit': IAMIntent.COMPLIANCE,
            'admin': IAMIntent.ADMIN_ACCESS,
            'administrator': IAMIntent.ADMIN_ACCESS,
            'operational': IAMIntent.OPERATIONAL_EFFICIENCY,
            'operations': IAMIntent.OPERATIONAL_EFFICIENCY,
            'automation': IAMIntent.AUTOMATION_ROLE,
            'deploy': IAMIntent.AUTOMATION_ROLE,
            'deployment': IAMIntent.AUTOMATION_ROLE
        }
        
        user_intent_lower = user_intent.lower().strip()
        return intent_mapping.get(user_intent_lower, IAMIntent.UNKNOWN)

    def _analyze_user_description(self, description: str) -> Tuple[IAMIntent, float, str]:
        """Analyze user's text description to infer intent."""
        description_lower = description.lower()
        
        # Security keywords
        security_keywords = ['security', 'secure', 'mfa', 'encryption', 'compliance', 'audit']
        if any(keyword in description_lower for keyword in security_keywords):
            return IAMIntent.STRONG_SECURITY, 0.9, f"Description contains security keywords"
        
        # Service account keywords
        service_keywords = ['service', 'application', 'app', 'system', 'automated', 'lambda', 'ec2']
        if any(keyword in description_lower for keyword in service_keywords):
            return IAMIntent.SERVICE_ACCOUNT, 0.8, f"Description contains service account keywords"
        
        # Developer keywords
        dev_keywords = ['developer', 'development', 'testing', 'sandbox', 'experimental']
        if any(keyword in description_lower for keyword in dev_keywords):
            return IAMIntent.DEVELOPER_FLEXIBILITY, 0.8, f"Description contains development keywords"
        
        # Admin keywords
        admin_keywords = ['admin', 'administrator', 'full access', 'everything', 'manage all']
        if any(keyword in description_lower for keyword in admin_keywords):
            return IAMIntent.ADMIN_ACCESS, 0.8, f"Description contains admin keywords"
        
        # Compliance keywords
        compliance_keywords = ['compliance', 'audit', 'readonly', 'monitor', 'logging', 'governance']
        if any(keyword in description_lower for keyword in compliance_keywords):
            return IAMIntent.COMPLIANCE, 0.8, f"Description contains compliance keywords"
        
        # Automation keywords
        automation_keywords = ['automation', 'deploy', 'pipeline', 'ci/cd', 'terraform', 'ansible']
        if any(keyword in description_lower for keyword in automation_keywords):
            return IAMIntent.AUTOMATION_ROLE, 0.8, f"Description contains automation keywords"
        
        return IAMIntent.UNKNOWN, 0.3, "No clear intent indicators in description"

    def _auto_detect_intent(self, resource_type: str, resource_name: str, client) -> Tuple[IAMIntent, float, str]:
        """Automatically detect intent based on resource analysis."""
        evidence = []
        confidence_scores = {}
        
        # 1. Analyze resource name
        name_intent, name_confidence, name_reason = self._analyze_resource_name(resource_name)
        if name_confidence > 0.5:
            evidence.append(name_reason)
            confidence_scores[name_intent] = name_confidence
        
        # 2. Analyze attached policies (for users and roles)
        if resource_type in ['user', 'role']:
            policy_intent, policy_confidence, policy_reason = self._analyze_attached_policies(client, resource_type, resource_name)
            if policy_confidence > 0.5:
                evidence.append(policy_reason)
                confidence_scores[policy_intent] = confidence_scores.get(policy_intent, 0) + policy_confidence
        
        # 3. Check trust policy (for roles)
        if resource_type == 'role':
            trust_intent, trust_confidence, trust_reason = self._analyze_trust_policy(client, resource_name)
            if trust_confidence > 0.5:
                evidence.append(trust_reason)
                confidence_scores[trust_intent] = confidence_scores.get(trust_intent, 0) + trust_confidence
        
        # 4. Check access patterns (for users)
        if resource_type == 'user':
            access_intent, access_confidence, access_reason = self._analyze_user_access_patterns(client, resource_name)
            if access_confidence > 0.5:
                evidence.append(access_reason)
                confidence_scores[access_intent] = confidence_scores.get(access_intent, 0) + access_confidence
        
        # 5. Analyze policy content (for policies)
        if resource_type == 'policy':
            content_intent, content_confidence, content_reason = self._analyze_policy_content(client, resource_name)
            if content_confidence > 0.5:
                evidence.append(content_reason)
                confidence_scores[content_intent] = confidence_scores.get(content_intent, 0) + content_confidence
        
        # Determine best intent
        if confidence_scores:
            best_intent = max(confidence_scores.items(), key=lambda x: x[1])
            intent, total_confidence = best_intent
            # Normalize confidence (max 1.0)
            normalized_confidence = min(total_confidence / 2.0, 1.0)
            reasoning = "; ".join(evidence)
            return intent, normalized_confidence, reasoning
        
        # If no clear intent indicators found, default based on resource type
        if resource_type == 'role':
            return IAMIntent.SERVICE_ACCOUNT, 0.3, "Role without clear intent indicators, defaulting to service account"
        elif resource_type == 'user':
            return IAMIntent.DEVELOPER_FLEXIBILITY, 0.3, "User without clear intent indicators, defaulting to developer flexibility"
        else:
            return IAMIntent.LEAST_PRIVILEGE, 0.3, "Policy without clear intent indicators, defaulting to least privilege"

    def _analyze_resource_name(self, resource_name: str) -> Tuple[IAMIntent, float, str]:
        """Analyze resource name for intent clues."""
        name_lower = resource_name.lower()
        
        # Service account patterns
        if any(indicator in name_lower for indicator in self.service_account_indicators):
            return IAMIntent.SERVICE_ACCOUNT, 0.7, f"Resource name suggests service account: '{resource_name}'"
        
        # Admin patterns
        if any(indicator in name_lower for indicator in self.admin_indicators):
            return IAMIntent.ADMIN_ACCESS, 0.8, f"Resource name suggests admin access: '{resource_name}'"
        
        # Developer patterns
        if any(indicator in name_lower for indicator in self.developer_indicators):
            return IAMIntent.DEVELOPER_FLEXIBILITY, 0.6, f"Resource name suggests developer use: '{resource_name}'"
        
        # Automation patterns
        if any(indicator in name_lower for indicator in self.automation_indicators):
            return IAMIntent.AUTOMATION_ROLE, 0.7, f"Resource name suggests automation: '{resource_name}'"
        
        # Compliance patterns
        if any(indicator in name_lower for indicator in self.compliance_indicators):
            return IAMIntent.COMPLIANCE, 0.6, f"Resource name suggests compliance: '{resource_name}'"
        
        return IAMIntent.UNKNOWN, 0.0, "No intent indicators in resource name"

    def _analyze_attached_policies(self, client, resource_type: str, resource_name: str) -> Tuple[IAMIntent, float, str]:
        """Analyze attached policies to infer intent."""
        try:
            if resource_type == 'user':
                policies = client.list_attached_user_policies(UserName=resource_name)
            elif resource_type == 'role':
                policies = client.list_attached_role_policies(RoleName=resource_name)
            else:
                return IAMIntent.UNKNOWN, 0.0, "Not applicable for this resource type"
            
            attached_policies = policies.get('AttachedPolicies', [])
            
            if not attached_policies:
                return IAMIntent.LEAST_PRIVILEGE, 0.4, "No attached policies suggest minimal access intent"
            
            # Check for admin policies
            admin_policies = [
                'AdministratorAccess', 'PowerUserAccess', 'IAMFullAccess'
            ]
            for policy in attached_policies:
                policy_name = policy['PolicyName']
                if any(admin in policy_name for admin in admin_policies):
                    return IAMIntent.ADMIN_ACCESS, 0.9, f"Has admin policy: {policy_name}"
            
            # Check for readonly/compliance policies
            readonly_policies = ['ReadOnlyAccess', 'SecurityAudit', 'ViewOnlyAccess']
            for policy in attached_policies:
                policy_name = policy['PolicyName']
                if any(readonly in policy_name for readonly in readonly_policies):
                    return IAMIntent.COMPLIANCE, 0.7, f"Has readonly/audit policy: {policy_name}"
            
            # Check for service-specific policies
            service_policies = ['AmazonEC2FullAccess', 'AmazonS3FullAccess', 'AWSLambdaExecute']
            service_count = 0
            for policy in attached_policies:
                policy_name = policy['PolicyName']
                if any(service in policy_name for service in service_policies):
                    service_count += 1
            
            if service_count > 0:
                return IAMIntent.SERVICE_ACCOUNT, 0.6, f"Has {service_count} service-specific policies"
            
            # Multiple policies suggest operational needs
            if len(attached_policies) > 3:
                return IAMIntent.OPERATIONAL_EFFICIENCY, 0.5, f"Has {len(attached_policies)} policies for operational needs"
            
            return IAMIntent.LEAST_PRIVILEGE, 0.4, f"Has {len(attached_policies)} policies, suggests controlled access"
            
        except Exception as e:
            return IAMIntent.UNKNOWN, 0.0, f"Error analyzing policies: {e}"

    def _analyze_trust_policy(self, client, role_name: str) -> Tuple[IAMIntent, float, str]:
        """Analyze role trust policy to infer intent."""
        try:
            role = client.get_role(RoleName=role_name)
            trust_policy = role['Role']['AssumeRolePolicyDocument']
            
            statements = trust_policy.get('Statement', [])
            if isinstance(statements, dict):
                statements = [statements]
            
            for statement in statements:
                principal = statement.get('Principal', {})
                
                # Check for AWS service principals
                if isinstance(principal, dict):
                    services = principal.get('Service', [])
                    if isinstance(services, str):
                        services = [services]
                    
                    # AWS service roles
                    aws_services = [s for s in services if s.endswith('.amazonaws.com')]
                    if aws_services:
                        service_name = aws_services[0].split('.')[0]
                        return IAMIntent.SERVICE_ACCOUNT, 0.9, f"Trust policy allows AWS service: {service_name}"
                    
                    # Check for federated principals (SAML, OIDC)
                    if 'Federated' in principal:
                        return IAMIntent.OPERATIONAL_EFFICIENCY, 0.7, "Trust policy allows federated access"
                    
                    # Check for cross-account access
                    aws_principals = principal.get('AWS', [])
                    if isinstance(aws_principals, str):
                        aws_principals = [aws_principals]
                    
                    external_accounts = [p for p in aws_principals if ':root' in p and not p.startswith('arn:aws:iam::' + client._get_caller_account_id())]
                    if external_accounts:
                        return IAMIntent.OPERATIONAL_EFFICIENCY, 0.6, f"Trust policy allows cross-account access"
            
            return IAMIntent.SERVICE_ACCOUNT, 0.5, "Standard role trust policy"
            
        except Exception as e:
            return IAMIntent.UNKNOWN, 0.0, f"Error analyzing trust policy: {e}"

    def _analyze_user_access_patterns(self, client, user_name: str) -> Tuple[IAMIntent, float, str]:
        """Analyze user access patterns to infer intent."""
        try:
            # Check if user has console access
            try:
                client.get_login_profile(UserName=user_name)
                has_console = True
            except:
                has_console = False
            
            # Check access keys
            access_keys = client.list_access_keys(UserName=user_name)
            key_count = len(access_keys.get('AccessKeyMetadata', []))
            
            # Check MFA devices
            mfa_devices = client.list_mfa_devices(UserName=user_name)
            has_mfa = len(mfa_devices.get('MFADevices', [])) > 0
            
            # Human user patterns
            if has_console and has_mfa:
                return IAMIntent.STRONG_SECURITY, 0.7, "Has console access with MFA - human user with security focus"
            elif has_console and not has_mfa:
                return IAMIntent.DEVELOPER_FLEXIBILITY, 0.6, "Has console access without MFA - developer user"
            
            # Service account patterns
            elif not has_console and key_count > 0:
                return IAMIntent.SERVICE_ACCOUNT, 0.8, "No console access but has API keys - service account"
            elif not has_console and key_count == 0:
                return IAMIntent.UNKNOWN, 0.2, "No console or API access - inactive or role-only user"
            
            return IAMIntent.UNKNOWN, 0.1, "Unclear access patterns"
            
        except Exception as e:
            return IAMIntent.UNKNOWN, 0.0, f"Error analyzing access patterns: {e}"

    def _analyze_policy_content(self, client, policy_arn: str) -> Tuple[IAMIntent, float, str]:
        """Analyze policy document content to infer intent."""
        try:
            # Get policy document
            policy = client.get_policy(PolicyArn=policy_arn)
            policy_version = client.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=policy['Policy']['DefaultVersionId']
            )
            
            policy_document = policy_version['PolicyVersion']['Document']
            statements = policy_document.get('Statement', [])
            if isinstance(statements, dict):
                statements = [statements]
            
            total_actions = 0
            wildcard_actions = 0
            readonly_actions = 0
            dangerous_actions = 0
            
            dangerous_action_patterns = ['*', 'iam:', 'sts:AssumeRole', 'Delete', 'Terminate']
            readonly_action_patterns = ['List', 'Get', 'Describe', 'View']
            
            for statement in statements:
                if statement.get('Effect') == 'Allow':
                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    total_actions += len(actions)
                    
                    for action in actions:
                        if '*' in action:
                            wildcard_actions += 1
                        
                        if any(danger in action for danger in dangerous_action_patterns):
                            dangerous_actions += 1
                        
                        if any(readonly in action for readonly in readonly_action_patterns):
                            readonly_actions += 1
            
            # Analyze intent based on action patterns
            if wildcard_actions > 0 and dangerous_actions > total_actions * 0.3:
                return IAMIntent.ADMIN_ACCESS, 0.8, f"Policy has wildcards and dangerous actions: {dangerous_actions}/{total_actions}"
            
            if readonly_actions > total_actions * 0.8:
                return IAMIntent.COMPLIANCE, 0.7, f"Policy is mostly readonly: {readonly_actions}/{total_actions}"
            
            if total_actions > 20:
                return IAMIntent.OPERATIONAL_EFFICIENCY, 0.6, f"Policy has many actions: {total_actions}"
            
            if total_actions <= 5:
                return IAMIntent.LEAST_PRIVILEGE, 0.7, f"Policy has few actions: {total_actions}"
            
            return IAMIntent.SERVICE_ACCOUNT, 0.4, f"Standard policy with {total_actions} actions"
            
        except Exception as e:
            return IAMIntent.UNKNOWN, 0.0, f"Error analyzing policy content: {e}"

    def get_intent_recommendations(self, intent: IAMIntent, resource_type: str, resource_name: str) -> Dict:
        """Get recommendations based on detected intent."""
        recommendations = {
            IAMIntent.LEAST_PRIVILEGE: {
                "security": {
                    "mfa": "Enable MFA for all users",
                    "policies": "Use minimal required permissions only",
                    "conditions": "Add conditions for IP, time, and MFA requirements"
                },
                "configuration": {
                    "access_keys": "Rotate access keys regularly (90 days max)",
                    "groups": "Use groups instead of direct policy attachment",
                    "roles": "Use roles for temporary access"
                },
                "best_practices": {
                    "monitoring": "Enable CloudTrail for all API activities",
                    "review": "Regular access review and permission audits"
                }
            },
            IAMIntent.STRONG_SECURITY: {
                "security": {
                    "mfa": "Require MFA for all console and API access",
                    "policies": "Use deny policies for sensitive actions",
                    "conditions": "Require MFA, IP restrictions, and time bounds"
                },
                "configuration": {
                    "access_keys": "Short-lived access keys (30-60 days)",
                    "password_policy": "Strong password policy with complexity requirements",
                    "session_duration": "Short session duration for roles"
                },
                "monitoring": {
                    "alerts": "Set up alerts for privilege escalation attempts",
                    "logging": "Comprehensive logging and monitoring"
                }
            },
            IAMIntent.SERVICE_ACCOUNT: {
                "security": {
                    "mfa": "No MFA required for service accounts",
                    "access_keys": "Use IAM roles instead of access keys when possible",
                    "policies": "Minimal permissions for specific services only"
                },
                "configuration": {
                    "trust_policy": "Restrict trust policy to specific services",
                    "conditions": "Add source IP or VPC conditions",
                    "session_duration": "Set appropriate session duration"
                },
                "best_practices": {
                    "rotation": "Automate credential rotation",
                    "monitoring": "Monitor for unusual API usage patterns"
                }
            },
            IAMIntent.DEVELOPER_FLEXIBILITY: {
                "security": {
                    "mfa": "Enable MFA for console access",
                    "sandbox": "Use sandbox environments for testing",
                    "policies": "Broad permissions within development boundaries"
                },
                "configuration": {
                    "environment": "Separate development, staging, production access",
                    "time_bounds": "Time-limited access to production resources",
                    "groups": "Use developer groups for permission management"
                },
                "best_practices": {
                    "training": "Security awareness training for developers",
                    "code_review": "Review IAM changes in code reviews"
                }
            },
            IAMIntent.COMPLIANCE: {
                "security": {
                    "readonly": "Prefer readonly access for audit functions",
                    "mfa": "Require MFA for all compliance users",
                    "logging": "Enable detailed logging for all activities"
                },
                "configuration": {
                    "separation": "Separate compliance roles from operational roles",
                    "approval": "Require approval for privilege changes",
                    "documentation": "Document all permission grants"
                },
                "monitoring": {
                    "auditing": "Regular compliance audits and reviews",
                    "reporting": "Automated compliance reporting"
                }
            },
            IAMIntent.ADMIN_ACCESS: {
                "security": {
                    "mfa": "Require MFA for all admin operations",
                    "break_glass": "Use break-glass procedures for emergency access",
                    "conditions": "Strict conditions on admin permissions"
                },
                "configuration": {
                    "just_in_time": "Use just-in-time access for admin operations",
                    "approval": "Multi-person approval for admin changes",
                    "monitoring": "Real-time monitoring of admin activities"
                },
                "best_practices": {
                    "principle": "Use admin access sparingly and temporarily",
                    "delegation": "Delegate specific admin tasks to specialized roles"
                }
            }
        }
        
        return recommendations.get(intent, {})