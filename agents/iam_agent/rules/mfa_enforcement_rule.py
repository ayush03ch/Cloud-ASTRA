# agents/iam_agent/rules/mfa_enforcement_rule.py

import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta


class MFAEnforcementRule:
    """
    Rule to detect and remediate missing MFA on IAM users,
    especially those with console access or sensitive permissions.
    """
    
    id = "iam_mfa_enforcement"
    detection = "IAM user lacks MFA device but has console access or sensitive permissions"
    auto_safe = True  # Can safely enable MFA requirement
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = True
        self.fix_type = None
        self.user_details = None
        self.risk_level = "medium"
    
    def check(self, client, user_name):
        """Check if user needs MFA enforcement."""
        try:
            # Get user details
            user_info = client.get_user(UserName=user_name)
            
            # Check if user has MFA devices
            mfa_devices = client.list_mfa_devices(UserName=user_name)
            has_mfa = len(mfa_devices.get('MFADevices', [])) > 0
            
            if has_mfa:
                print(f"✅ User {user_name} already has MFA enabled")
                return False
            
            # Check if user has console access
            has_console_access = self._check_console_access(client, user_name)
            
            # Check if user has sensitive permissions
            has_sensitive_permissions = self._check_sensitive_permissions(client, user_name)
            
            # Check if user has been active recently
            is_active_user = self._check_user_activity(client, user_name)
            
            # Determine if MFA should be enforced
            if has_console_access or has_sensitive_permissions:
                self.risk_level = "high" if has_sensitive_permissions else "medium"
                self.user_details = {
                    "has_console_access": has_console_access,
                    "has_sensitive_permissions": has_sensitive_permissions,
                    "is_active": is_active_user,
                    "creation_date": user_info['User']['CreateDate'].isoformat()
                }
                
                self._set_fix_instructions(user_name)
                print(f"🔴 MFA missing for user {user_name} with {self.risk_level} risk")
                return True
            
            print(f"ℹ️ User {user_name} has no console access or sensitive permissions - MFA not critical")
            return False
            
        except ClientError as e:
            print(f"❌ Error checking MFA for user {user_name}: {e}")
            return False
    
    def _check_console_access(self, client, user_name):
        """Check if user has console login profile."""
        try:
            client.get_login_profile(UserName=user_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                return False
            raise
    
    def _check_sensitive_permissions(self, client, user_name):
        """Check if user has sensitive permissions that require MFA."""
        try:
            # Check attached managed policies
            attached_policies = client.list_attached_user_policies(UserName=user_name)
            for policy in attached_policies.get('AttachedPolicies', []):
                policy_arn = policy['PolicyArn']
                
                # High-risk AWS managed policies
                sensitive_policies = [
                    'arn:aws:iam::aws:policy/AdministratorAccess',
                    'arn:aws:iam::aws:policy/PowerUserAccess',
                    'arn:aws:iam::aws:policy/IAMFullAccess',
                    'arn:aws:iam::aws:policy/SecurityAudit',
                    'arn:aws:iam::aws:policy/ReadOnlyAccess'
                ]
                
                if any(sensitive in policy_arn for sensitive in sensitive_policies):
                    return True
            
            # Check inline policies for sensitive actions
            inline_policies = client.list_user_policies(UserName=user_name)
            for policy_name in inline_policies.get('PolicyNames', []):
                policy_doc = client.get_user_policy(UserName=user_name, PolicyName=policy_name)
                if self._has_sensitive_actions(policy_doc['PolicyDocument']):
                    return True
            
            # Check group memberships
            groups = client.get_groups_for_user(UserName=user_name)
            for group in groups.get('Groups', []):
                if self._check_group_sensitive_permissions(client, group['GroupName']):
                    return True
            
            return False
            
        except ClientError as e:
            print(f"⚠️ Error checking permissions for {user_name}: {e}")
            return False
    
    def _has_sensitive_actions(self, policy_document):
        """Check if policy document contains sensitive actions."""
        sensitive_actions = [
            'iam:*', 'sts:AssumeRole', '*:*',
            'ec2:TerminateInstances', 's3:DeleteBucket',
            'rds:DeleteDBInstance', 'dynamodb:DeleteTable'
        ]
        
        statements = policy_document.get('Statement', [])
        if isinstance(statements, dict):
            statements = [statements]
        
        for statement in statements:
            if statement.get('Effect') == 'Allow':
                actions = statement.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                
                for action in actions:
                    if any(sensitive in action for sensitive in sensitive_actions):
                        return True
        
        return False
    
    def _check_group_sensitive_permissions(self, client, group_name):
        """Check if group has sensitive permissions."""
        try:
            # Check group's attached policies
            attached_policies = client.list_attached_group_policies(GroupName=group_name)
            for policy in attached_policies.get('AttachedPolicies', []):
                if 'Administrator' in policy['PolicyArn'] or 'PowerUser' in policy['PolicyArn']:
                    return True
            return False
        except ClientError:
            return False
    
    def _check_user_activity(self, client, user_name):
        """Check if user has been active recently."""
        try:
            # Check access key last used
            access_keys = client.list_access_keys(UserName=user_name)
            for key_metadata in access_keys.get('AccessKeyMetadata', []):
                try:
                    last_used = client.get_access_key_last_used(AccessKeyId=key_metadata['AccessKeyId'])
                    last_used_date = last_used.get('AccessKeyLastUsed', {}).get('LastUsedDate')
                    if last_used_date and (datetime.now() - last_used_date.replace(tzinfo=None)).days < 30:
                        return True
                except ClientError:
                    continue
            
            return False  # No recent activity detected
            
        except ClientError:
            return True  # Assume active if we can't determine
    
    def _set_fix_instructions(self, user_name):
        """Set instructions for enabling MFA."""
        self.fix_instructions = [
            f"🔐 MFA Enforcement Required for User: {user_name}",
            "",
            f"Risk Level: {self.risk_level.upper()}",
            f"Console Access: {'Yes' if self.user_details['has_console_access'] else 'No'}",
            f"Sensitive Permissions: {'Yes' if self.user_details['has_sensitive_permissions'] else 'No'}",
            "",
            "🔧 MFA Setup Steps:",
            "1. User must set up virtual MFA device (Google Authenticator, Authy, etc.)",
            "2. Scan QR code with authenticator app",
            "3. Enter two consecutive MFA codes to activate",
            "4. (Optional) Set up backup MFA device",
            "",
            "🔒 Enforcement Options:",
            "Option 1: Force MFA on next login (recommended)",
            "Option 2: Add MFA condition to existing policies",
            "Option 3: Create MFA-required group and add user",
            "",
            "⚠️ Impact: User will need MFA device for future logins"
        ]
        
        self.can_auto_fix = True
        self.fix_type = "enforce_mfa_policy"
    
    def fix(self, client, user_name):
        """Apply MFA enforcement by adding policy condition."""
        try:
            print(f"🔧 Enforcing MFA requirement for user: {user_name}")
            
            # Create MFA-required policy if it doesn't exist
            mfa_policy_name = "EnforceMFAPolicy"
            mfa_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Deny",
                        "Action": "*",
                        "Resource": "*",
                        "Condition": {
                            "Bool": {
                                "aws:MultiFactorAuthPresent": "false"
                            }
                        }
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "iam:CreateVirtualMFADevice",
                            "iam:EnableMFADevice",
                            "iam:GetUser",
                            "iam:ListMFADevices",
                            "iam:ListVirtualMFADevices",
                            "iam:ResyncMFADevice",
                            "sts:GetSessionToken"
                        ],
                        "Resource": "*"
                    }
                ]
            }
            
            # Try to create the policy (may already exist)
            try:
                policy_arn = f"arn:aws:iam::{client._get_caller_account_id()}:policy/{mfa_policy_name}"
                client.create_policy(
                    PolicyName=mfa_policy_name,
                    PolicyDocument=json.dumps(mfa_policy_document),
                    Description="Enforces MFA for all actions except MFA setup"
                )
                print(f"✅ Created MFA enforcement policy: {mfa_policy_name}")
            except ClientError as e:
                if e.response['Error']['Code'] != 'EntityAlreadyExists':
                    raise
                # Policy already exists, get its ARN
                account_id = client.get_user()['User']['Arn'].split(':')[4]
                policy_arn = f"arn:aws:iam::{account_id}:policy/{mfa_policy_name}"
            
            # Attach the policy to the user
            client.attach_user_policy(UserName=user_name, PolicyArn=policy_arn)
            
            print(f"✅ MFA enforcement policy attached to user {user_name}")
            print(f"ℹ️ User will be required to set up MFA on next login")
            
            return {
                "success": True,
                "message": f"MFA enforcement enabled for user {user_name}",
                "policy_attached": mfa_policy_name,
                "next_steps": [
                    "User must set up MFA device on next login",
                    "Provide user with MFA setup instructions",
                    "Monitor for successful MFA activation"
                ]
            }
            
        except ClientError as e:
            error_msg = f"Failed to enforce MFA for user {user_name}: {e}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "recommendation": "Manual MFA setup required"
            }