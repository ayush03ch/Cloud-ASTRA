# agents/iam_agent/rules/least_privilege_rule.py

import boto3
from botocore.exceptions import ClientError
import json


class LeastPrivilegeRule:
    """
    Rule to detect and remediate overly permissive IAM policies,
    users with excessive permissions, and violation of least privilege principle.
    """
    
    id = "iam_least_privilege"
    detection = "IAM entity has excessive permissions violating least privilege principle"
    auto_safe = False  # Requires manual review for permission reduction
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = False
        self.fix_type = None
        self.privilege_violations = None
        self.risk_score = 0
    
    def check(self, client, entity_type, entity_name):
        """Check if entity violates least privilege principle."""
        try:
            violations = []
            
            if entity_type == "user":
                violations.extend(self._check_user_privileges(client, entity_name))
            elif entity_type == "role":
                violations.extend(self._check_role_privileges(client, entity_name))
            elif entity_type == "policy":
                violations.extend(self._check_policy_privileges(client, entity_name))
            
            if violations:
                self.privilege_violations = violations
                self.risk_score = self._calculate_risk_score(violations)
                self._set_fix_instructions(entity_type, entity_name, violations)
                print(f"🔴 Least privilege violations found for {entity_type} {entity_name} (Risk Score: {self.risk_score})")
                return True
            
            print(f"✅ {entity_type.title()} {entity_name} follows least privilege principle")
            return False
            
        except ClientError as e:
            print(f"❌ Error checking least privilege for {entity_type} {entity_name}: {e}")
            return False
    
    def _check_user_privileges(self, client, user_name):
        """Check user for privilege violations."""
        violations = []
        
        try:
            # Check attached managed policies
            attached_policies = client.list_attached_user_policies(UserName=user_name)
            for policy in attached_policies.get('AttachedPolicies', []):
                policy_arn = policy['PolicyArn']
                
                # Check for high-risk AWS managed policies
                if self._is_high_risk_aws_policy(policy_arn):
                    violations.append({
                        "type": "high_risk_aws_policy",
                        "resource": policy['PolicyName'],
                        "arn": policy_arn,
                        "description": f"User has high-risk AWS managed policy: {policy['PolicyName']}",
                        "recommendation": "Replace with custom policy with minimal required permissions"
                    })
                
                # Analyze customer managed policies
                if not policy_arn.startswith('arn:aws:iam::aws:policy/'):
                    policy_violations = self._analyze_policy_document(client, policy_arn)
                    violations.extend(policy_violations)
            
            # Check inline policies
            inline_policies = client.list_user_policies(UserName=user_name)
            for policy_name in inline_policies.get('PolicyNames', []):
                policy_doc = client.get_user_policy(UserName=user_name, PolicyName=policy_name)
                inline_violations = self._analyze_inline_policy(policy_doc['PolicyDocument'], policy_name)
                violations.extend(inline_violations)
            
            # Check group memberships for inherited violations
            try:
                groups = client.list_groups_for_user(UserName=user_name)
                for group in groups.get('Groups', []):
                    group_violations = self._check_group_privileges(client, group['GroupName'])
                    for violation in group_violations:
                        violation['inherited_from_group'] = group['GroupName']
                    violations.extend(group_violations)
            except ClientError:
                pass  # Skip if no permission to list groups
            
        except ClientError as e:
            print(f"⚠️ Error analyzing user privileges for {user_name}: {e}")
        
        return violations
    
    def _check_role_privileges(self, client, role_name):
        """Check role for privilege violations."""
        violations = []
        
        try:
            # Get role information
            role_info = client.get_role(RoleName=role_name)
            
            # Check trust policy
            trust_policy = role_info['Role']['AssumeRolePolicyDocument']
            trust_violations = self._analyze_trust_policy(trust_policy, role_name)
            violations.extend(trust_violations)
            
            # Check attached managed policies
            attached_policies = client.list_attached_role_policies(RoleName=role_name)
            for policy in attached_policies.get('AttachedPolicies', []):
                policy_arn = policy['PolicyArn']
                
                if self._is_high_risk_aws_policy(policy_arn):
                    violations.append({
                        "type": "high_risk_aws_policy",
                        "resource": policy['PolicyName'],
                        "arn": policy_arn,
                        "description": f"Role has high-risk AWS managed policy: {policy['PolicyName']}",
                        "recommendation": "Replace with custom policy with minimal required permissions"
                    })
                
                if not policy_arn.startswith('arn:aws:iam::aws:policy/'):
                    policy_violations = self._analyze_policy_document(client, policy_arn)
                    violations.extend(policy_violations)
            
            # Check inline policies
            inline_policies = client.list_role_policies(RoleName=role_name)
            for policy_name in inline_policies.get('PolicyNames', []):
                policy_doc = client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                inline_violations = self._analyze_inline_policy(policy_doc['PolicyDocument'], policy_name)
                violations.extend(inline_violations)
            
        except ClientError as e:
            print(f"⚠️ Error analyzing role privileges for {role_name}: {e}")
        
        return violations
    
    def _check_policy_privileges(self, client, policy_arn):
        """Check managed policy for privilege violations."""
        violations = []
        
        try:
            # Get policy document
            policy_info = client.get_policy(PolicyArn=policy_arn)
            policy_version = client.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=policy_info['Policy']['DefaultVersionId']
            )
            
            policy_document = policy_version['PolicyVersion']['Document']
            policy_name = policy_info['Policy']['PolicyName']
            
            violations.extend(self._analyze_inline_policy(policy_document, policy_name))
            
        except ClientError as e:
            print(f"⚠️ Error analyzing policy {policy_arn}: {e}")
        
        return violations
    
    def _analyze_policy_document(self, client, policy_arn):
        """Analyze a managed policy document for violations."""
        try:
            policy_info = client.get_policy(PolicyArn=policy_arn)
            policy_version = client.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=policy_info['Policy']['DefaultVersionId']
            )
            
            policy_document = policy_version['PolicyVersion']['Document']
            policy_name = policy_info['Policy']['PolicyName']
            
            return self._analyze_inline_policy(policy_document, policy_name)
            
        except ClientError:
            return []
    
    def _analyze_inline_policy(self, policy_document, policy_name):
        """Analyze policy document for least privilege violations."""
        violations = []
        
        statements = policy_document.get('Statement', [])
        if isinstance(statements, dict):
            statements = [statements]
        
        for i, statement in enumerate(statements):
            if statement.get('Effect') != 'Allow':
                continue
            
            # Check for wildcard actions
            actions = statement.get('Action', [])
            if isinstance(actions, str):
                actions = [actions]
            
            resources = statement.get('Resource', [])
            if isinstance(resources, str):
                resources = [resources]
            
            # Check for dangerous wildcard combinations
            wildcard_actions = [action for action in actions if '*' in action]
            wildcard_resources = [resource for resource in resources if resource == '*']
            
            if '*' in actions and '*' in resources:
                violations.append({
                    "type": "full_wildcard_access",
                    "resource": policy_name,
                    "statement_index": i,
                    "description": "Policy grants full access to all actions on all resources (*:*)",
                    "recommendation": "Replace with specific actions and resources needed",
                    "severity": "critical"
                })
            elif wildcard_actions and len(actions) == len(wildcard_actions):
                violations.append({
                    "type": "wildcard_actions",
                    "resource": policy_name,
                    "statement_index": i,
                    "actions": wildcard_actions,
                    "description": f"Policy uses wildcard actions: {', '.join(wildcard_actions)}",
                    "recommendation": "Replace wildcards with specific actions",
                    "severity": "high"
                })
            
            # Check for sensitive actions
            sensitive_actions = [
                'iam:CreateUser', 'iam:CreateRole', 'iam:AttachUserPolicy',
                'iam:AttachRolePolicy', 'iam:PutUserPolicy', 'iam:PutRolePolicy',
                'sts:AssumeRole', 'ec2:TerminateInstances', 's3:DeleteBucket',
                'rds:DeleteDBInstance', 'dynamodb:DeleteTable'
            ]
            
            found_sensitive = [action for action in actions if any(sens in action for sens in sensitive_actions)]
            if found_sensitive:
                violations.append({
                    "type": "sensitive_actions",
                    "resource": policy_name,
                    "statement_index": i,
                    "actions": found_sensitive,
                    "description": f"Policy allows sensitive actions: {', '.join(found_sensitive)}",
                    "recommendation": "Add conditions or remove if not necessary",
                    "severity": "high"
                })
            
            # Check for missing conditions on sensitive actions
            conditions = statement.get('Condition', {})
            if found_sensitive and not conditions:
                violations.append({
                    "type": "missing_conditions",
                    "resource": policy_name,
                    "statement_index": i,
                    "description": "Sensitive actions lack protective conditions (MFA, IP, time)",
                    "recommendation": "Add conditions like MFA requirement, IP restrictions",
                    "severity": "medium"
                })
        
        return violations
    
    def _analyze_trust_policy(self, trust_policy, role_name):
        """Analyze role trust policy for violations."""
        violations = []
        
        statements = trust_policy.get('Statement', [])
        if isinstance(statements, dict):
            statements = [statements]
        
        for i, statement in enumerate(statements):
            principal = statement.get('Principal', {})
            
            # Check for overly broad trust relationships
            if principal == '*':
                violations.append({
                    "type": "wildcard_trust_policy",
                    "resource": role_name,
                    "statement_index": i,
                    "description": "Role trust policy allows assumption by any principal (*)",
                    "recommendation": "Specify exact AWS accounts, users, or services",
                    "severity": "critical"
                })
            elif isinstance(principal, dict):
                aws_principals = principal.get('AWS', [])
                if isinstance(aws_principals, str):
                    aws_principals = [aws_principals]
                
                # Check for root account access
                root_access = [p for p in aws_principals if p.endswith(':root')]
                if root_access:
                    violations.append({
                        "type": "root_account_trust",
                        "resource": role_name,
                        "statement_index": i,
                        "principals": root_access,
                        "description": f"Role allows assumption by root accounts: {', '.join(root_access)}",
                        "recommendation": "Specify individual users or roles instead of root",
                        "severity": "high"
                    })
        
        return violations
    
    def _check_group_privileges(self, client, group_name):
        """Check group for privilege violations."""
        violations = []
        
        try:
            # Check group's attached policies
            attached_policies = client.list_attached_group_policies(GroupName=group_name)
            for policy in attached_policies.get('AttachedPolicies', []):
                if self._is_high_risk_aws_policy(policy['PolicyArn']):
                    violations.append({
                        "type": "group_high_risk_policy",
                        "resource": f"Group: {group_name}",
                        "policy": policy['PolicyName'],
                        "description": f"Group has high-risk policy: {policy['PolicyName']}",
                        "recommendation": "Review group membership and policy necessity"
                    })
        except ClientError:
            pass
        
        return violations
    
    def _is_high_risk_aws_policy(self, policy_arn):
        """Check if AWS managed policy is high-risk."""
        high_risk_policies = [
            'arn:aws:iam::aws:policy/AdministratorAccess',
            'arn:aws:iam::aws:policy/PowerUserAccess',
            'arn:aws:iam::aws:policy/IAMFullAccess'
        ]
        return policy_arn in high_risk_policies
    
    def _calculate_risk_score(self, violations):
        """Calculate overall risk score based on violations."""
        score = 0
        severity_weights = {
            'critical': 10,
            'high': 5,
            'medium': 2,
            'low': 1
        }
        
        for violation in violations:
            severity = violation.get('severity', 'medium')
            score += severity_weights.get(severity, 2)
        
        return min(score, 100)  # Cap at 100
    
    def _set_fix_instructions(self, entity_type, entity_name, violations):
        """Set instructions for fixing least privilege violations."""
        self.fix_instructions = [
            f"🔒 Least Privilege Violations for {entity_type.title()}: {entity_name}",
            f"Risk Score: {self.risk_score}/100",
            "🔍 Violations Found:"
        ]
        
        for i, violation in enumerate(violations, 1):
            self.fix_instructions.extend([
                f"{i}. {violation['description']}",
                f"   → {violation['recommendation']}",
                f"   Severity: {violation.get('severity', 'medium').upper()}"
            ])
        
        self.fix_instructions.extend([
            "🔧 Remediation Steps:",
            "1. Review each violation carefully",
            "2. Create new policies with minimal required permissions",
            "3. Test new policies in non-production environment",
            "4. Replace existing policies gradually",
            "5. Monitor for access denied errors",
            "⚠️ Impact: May temporarily restrict access - test thoroughly"
        ])
        
        # Least privilege violations always require manual review - too risky to auto-fix
        self.can_auto_fix = False
        self.fix_type = "reduce_privileges"
    
    def fix(self, client, entity_type, entity_name):
        """Attempt to fix least privilege violations (limited auto-fixes)."""
        try:
            print(f"🔧 Attempting to fix least privilege violations for {entity_type} {entity_name}")
            
            if not self.can_auto_fix:
                return {
                    "success": False,
                    "message": "High-risk violations require manual review",
                    "violations": self.privilege_violations,
                    "recommendation": "Review and fix manually to avoid access issues"
                }
            
            # Only perform safe auto-fixes
            fixes_applied = []
            
            for violation in self.privilege_violations:
                if violation['type'] == 'missing_conditions':
                    # Add MFA condition to policies with sensitive actions
                    result = self._add_mfa_condition(client, entity_type, entity_name, violation)
                    if result:
                        fixes_applied.append(f"Added MFA condition to {violation['resource']}")
            
            if fixes_applied:
                return {
                    "success": True,
                    "message": f"Applied {len(fixes_applied)} safe fixes",
                    "fixes": fixes_applied,
                    "remaining_violations": [v for v in self.privilege_violations if v['type'] != 'missing_conditions']
                }
            else:
                return {
                    "success": False,
                    "message": "No safe auto-fixes available",
                    "recommendation": "Manual review required for all violations"
                }
                
        except ClientError as e:
            return {
                "success": False,
                "message": f"Error applying fixes: {e}",
                "recommendation": "Manual remediation required"
            }
    
    def _add_mfa_condition(self, client, entity_type, entity_name, violation):
        """Add MFA condition to a policy statement (safe fix)."""
        # This would require policy modification - complex implementation
        # For now, return False to indicate manual fix needed
        return False
