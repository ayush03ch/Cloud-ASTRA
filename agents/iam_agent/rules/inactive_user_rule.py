# agents/iam_agent/rules/inactive_user_rule.py

import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta


class InactiveUserRule:
    """
    Rule to detect and remediate inactive IAM users who haven't 
    logged in or used access keys for an extended period.
    """
    
    id = "iam_inactive_user"
    detection = "IAM user has been inactive for extended period"
    auto_safe = True  # Can safely disable inactive users
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = True
        self.fix_type = None
        self.inactive_users = None
        self.inactive_threshold_days = 90
        self.warning_threshold_days = 60
    
    def check(self, client, user_name=None, inactive_days_threshold=90):
        """Check for inactive users."""
        self.inactive_threshold_days = inactive_days_threshold
        self.warning_threshold_days = inactive_days_threshold - 30
        
        try:
            inactive_users = []
            
            if user_name:
                # Check specific user
                user_info = self._check_user_activity(client, user_name)
                if user_info and user_info['is_inactive']:
                    inactive_users.append(user_info)
            else:
                # Check all users in account
                users = client.list_users()
                for user in users.get('Users', [])[:100]:  # Limit to first 100 users
                    user_info = self._check_user_activity(client, user['UserName'])
                    if user_info and user_info['is_inactive']:
                        inactive_users.append(user_info)
            
            if inactive_users:
                self.inactive_users = inactive_users
                self._set_fix_instructions(inactive_users)
                print(f"🔴 Found {len(inactive_users)} inactive users")
                return True
            
            print(f"✅ All users have been active within {inactive_days_threshold} days")
            return False
            
        except ClientError as e:
            print(f"❌ Error checking inactive users: {e}")
            return False
    
    def _check_user_activity(self, client, user_name):
        """Check activity for a specific user."""
        try:
            # Get user creation date
            user_info = client.get_user(UserName=user_name)
            user_created = user_info['User']['CreateDate']
            if hasattr(user_created, 'replace'):
                user_created = user_created.replace(tzinfo=None)
            
            user_age_days = (datetime.utcnow() - user_created).days
            
            # Skip very new users
            if user_age_days < 7:
                return None
            
            activity_info = {
                'user_name': user_name,
                'creation_date': user_created.isoformat(),
                'user_age_days': user_age_days,
                'console_last_login': None,
                'access_key_last_used': None,
                'days_since_console_login': None,
                'days_since_key_usage': None,
                'has_console_access': False,
                'active_access_keys': 0,
                'total_access_keys': 0,
                'attached_policies': 0,
                'group_memberships': 0,
                'is_inactive': False,
                'inactivity_reason': [],
                'severity': 'low'
            }
            
            # Check console activity
            console_activity = self._get_console_activity(client, user_name)
            activity_info.update(console_activity)
            
            # Check access key activity
            key_activity = self._get_access_key_activity(client, user_name)
            activity_info.update(key_activity)
            
            # Check user permissions and associations
            permissions_info = self._get_user_permissions_info(client, user_name)
            activity_info.update(permissions_info)
            
            # Determine if user is inactive
            inactivity_analysis = self._analyze_inactivity(activity_info)
            activity_info.update(inactivity_analysis)
            
            return activity_info if activity_info['is_inactive'] else None
            
        except ClientError as e:
            print(f"⚠️ Error checking activity for user {user_name}: {e}")
            return None
    
    def _get_console_activity(self, client, user_name):
        """Get console login activity."""
        console_info = {
            'has_console_access': False,
            'console_last_login': None,
            'days_since_console_login': None
        }
        
        try:
            # Check if user has login profile (console access)
            login_profile = client.get_login_profile(UserName=user_name)
            console_info['has_console_access'] = True
            
            # Try to get password last used (not always available in basic IAM)
            # This would require CloudTrail or other logging services
            # For now, we'll mark as unknown
            console_info['console_last_login'] = 'unknown'
            
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchEntity':
                print(f"⚠️ Error checking console access for {user_name}: {e}")
        
        return console_info
    
    def _get_access_key_activity(self, client, user_name):
        """Get access key usage activity."""
        key_info = {
            'access_key_last_used': None,
            'days_since_key_usage': None,
            'active_access_keys': 0,
            'total_access_keys': 0,
            'key_details': []
        }
        
        try:
            access_keys = client.list_access_keys(UserName=user_name)
            key_info['total_access_keys'] = len(access_keys.get('AccessKeyMetadata', []))
            
            most_recent_usage = None
            
            for key_metadata in access_keys.get('AccessKeyMetadata', []):
                access_key_id = key_metadata['AccessKeyId']
                key_status = key_metadata['Status']
                key_age = (datetime.utcnow() - key_metadata['CreateDate'].replace(tzinfo=None)).days
                
                if key_status == 'Active':
                    key_info['active_access_keys'] += 1
                
                # Get last used info
                try:
                    last_used_response = client.get_access_key_last_used(AccessKeyId=access_key_id)
                    last_used_data = last_used_response.get('AccessKeyLastUsed', {})
                    last_used_date = last_used_data.get('LastUsedDate')
                    
                    key_detail = {
                        'key_id': access_key_id[:8] + '***',
                        'status': key_status,
                        'age_days': key_age,
                        'last_used_date': last_used_date.isoformat() if last_used_date else None,
                        'last_used_service': last_used_data.get('ServiceName', 'Unknown'),
                        'never_used': last_used_date is None
                    }
                    
                    if last_used_date:
                        if hasattr(last_used_date, 'replace'):
                            last_used_date = last_used_date.replace(tzinfo=None)
                        
                        key_detail['days_since_last_use'] = (datetime.utcnow() - last_used_date).days
                        
                        # Track most recent usage across all keys
                        if not most_recent_usage or last_used_date > most_recent_usage:
                            most_recent_usage = last_used_date
                    
                    key_info['key_details'].append(key_detail)
                    
                except ClientError as e:
                    key_info['key_details'].append({
                        'key_id': access_key_id[:8] + '***',
                        'status': key_status,
                        'age_days': key_age,
                        'error': str(e)
                    })
            
            if most_recent_usage:
                key_info['access_key_last_used'] = most_recent_usage.isoformat()
                key_info['days_since_key_usage'] = (datetime.utcnow() - most_recent_usage).days
            
        except ClientError as e:
            print(f"⚠️ Error checking access keys for {user_name}: {e}")
        
        return key_info
    
    def _get_user_permissions_info(self, client, user_name):
        """Get user permissions and group information."""
        permissions_info = {
            'attached_policies': 0,
            'inline_policies': 0,
            'group_memberships': 0,
            'group_names': [],
            'policy_names': []
        }
        
        try:
            # Check attached managed policies
            attached_policies = client.list_attached_user_policies(UserName=user_name)
            permissions_info['attached_policies'] = len(attached_policies.get('AttachedPolicies', []))
            permissions_info['policy_names'] = [p['PolicyName'] for p in attached_policies.get('AttachedPolicies', [])]
            
            # Check inline policies
            inline_policies = client.list_user_policies(UserName=user_name)
            permissions_info['inline_policies'] = len(inline_policies.get('PolicyNames', []))
            
            # Check group memberships
            groups = client.get_groups_for_user(UserName=user_name)
            permissions_info['group_memberships'] = len(groups.get('Groups', []))
            permissions_info['group_names'] = [g['GroupName'] for g in groups.get('Groups', [])]
            
        except ClientError as e:
            print(f"⚠️ Error checking permissions for {user_name}: {e}")
        
        return permissions_info
    
    def _analyze_inactivity(self, activity_info):
        """Analyze user activity to determine if inactive."""
        inactivity_reasons = []
        is_inactive = False
        severity = 'low'
        
        user_age = activity_info['user_age_days']
        
        # Check console inactivity
        if activity_info['has_console_access']:
            if activity_info['console_last_login'] == 'unknown':
                if user_age > self.inactive_threshold_days:
                    inactivity_reasons.append(f"Console access enabled but no recent login data (user age: {user_age} days)")
            # If we had actual login dates, we'd check them here
        
        # Check access key inactivity
        if activity_info['days_since_key_usage']:
            if activity_info['days_since_key_usage'] > self.inactive_threshold_days:
                inactivity_reasons.append(f"Access keys not used for {activity_info['days_since_key_usage']} days")
                is_inactive = True
                severity = 'high'
        elif activity_info['active_access_keys'] == 0 and activity_info['total_access_keys'] == 0:
            # No access keys at all
            if not activity_info['has_console_access'] and user_age > self.warning_threshold_days:
                inactivity_reasons.append(f"No access keys and no console access (user age: {user_age} days)")
                is_inactive = True
                severity = 'medium'
        elif activity_info['active_access_keys'] > 0:
            # Has active keys but never used them
            never_used_keys = [k for k in activity_info.get('key_details', []) if k.get('never_used')]
            if len(never_used_keys) == activity_info['active_access_keys'] and user_age > self.warning_threshold_days:
                inactivity_reasons.append(f"Active access keys never used (user age: {user_age} days)")
                is_inactive = True
                severity = 'medium'
        
        # Check if user has permissions but no activity
        has_permissions = (activity_info['attached_policies'] > 0 or 
                          activity_info['inline_policies'] > 0 or 
                          activity_info['group_memberships'] > 0)
        
        if has_permissions and not activity_info['has_console_access'] and activity_info['active_access_keys'] == 0:
            inactivity_reasons.append("Has permissions but no way to use them (no console access or active keys)")
            is_inactive = True
        
        # Special case: Very old users with no recent activity
        if user_age > self.inactive_threshold_days * 2:  # 180 days default
            if not inactivity_reasons:  # No specific reasons found, but very old
                inactivity_reasons.append(f"Very old user ({user_age} days) with unclear activity status")
                is_inactive = True
                severity = 'low'
        
        return {
            'is_inactive': is_inactive,
            'inactivity_reason': inactivity_reasons,
            'severity': severity,
            'risk_level': severity
        }
    
    def _set_fix_instructions(self, inactive_users):
        """Set instructions for handling inactive users."""
        critical_users = [u for u in inactive_users if u['severity'] == 'high']
        medium_users = [u for u in inactive_users if u['severity'] == 'medium']
        low_users = [u for u in inactive_users if u['severity'] == 'low']
        
        self.fix_instructions = [
            f"👤 Inactive User Management",
            f"Total Inactive: {len(inactive_users)} | High Risk: {len(critical_users)} | Medium: {len(medium_users)} | Low: {len(low_users)}",
            "🚨 High Risk Inactive Users:"
        ]
        
        for user in critical_users[:5]:  # Show first 5
            self.fix_instructions.extend([
                f"• {user['user_name']} (Age: {user['user_age_days']} days)",
                f"  Keys: {user['active_access_keys']} active, Last used: {user['days_since_key_usage'] or 'Never'} days ago",
                f"  Policies: {user['attached_policies']} attached, Groups: {user['group_memberships']}",
                f"  Reason: {'; '.join(user['inactivity_reason'])[:100]}..."
            ])
        
        self.fix_instructions.extend([
            "🔧 Inactive User Remediation Options:",
            "Option 1: Disable User (Reversible)",
            "1. Deactivate all access keys",
            "2. Remove login profile (console access)",
            "3. Keep user and policies for potential reactivation",
            "4. Monitor for 30 days before deletion",
            "Option 2: Remove Permissions (Conservative)",
            "1. Detach all policies",
            "2. Remove from all groups",
            "3. Keep user account but remove access",
            "4. Re-enable when user becomes active",
            "Option 3: Full Cleanup (Irreversible)",
            "1. Delete all access keys",
            "2. Delete login profile",
            "3. Detach all policies and remove from groups",
            "4. Delete user account",
            "⚠️ Impact: Users will lose all access immediately"
        ])
        
        # Can auto-fix by disabling (safest option)
        self.can_auto_fix = True
        self.fix_type = "disable_inactive_users"
    
    def fix(self, client, fix_option="disable", auto_approve=False):
        """Fix inactive users using specified option."""
        try:
            if not self.inactive_users:
                return {"success": False, "message": "No inactive users to process"}
            
            if not auto_approve and fix_option in ["remove_permissions", "delete"]:
                return {
                    "success": False,
                    "message": f"Option '{fix_option}' requires explicit approval",
                    "users_affected": len(self.inactive_users)
                }
            
            print(f"🔧 Processing {len(self.inactive_users)} inactive users with option: {fix_option}")
            
            if fix_option == "disable":
                return self._disable_users(client)
            elif fix_option == "remove_permissions":
                return self._remove_user_permissions(client)
            elif fix_option == "delete":
                return self._delete_users(client)
            else:
                return {"success": False, "message": f"Unknown fix option: {fix_option}"}
                
        except ClientError as e:
            return {
                "success": False,
                "message": f"Error processing inactive users: {e}"
            }
    
    def _disable_users(self, client):
        """Disable users by deactivating keys and removing console access."""
        disabled_users = []
        errors = []
        
        for user_info in self.inactive_users:
            user_name = user_info['user_name']
            
            try:
                # Deactivate all access keys
                keys_deactivated = 0
                access_keys = client.list_access_keys(UserName=user_name)
                
                for key_metadata in access_keys.get('AccessKeyMetadata', []):
                    if key_metadata['Status'] == 'Active':
                        try:
                            client.update_access_key(
                                UserName=user_name,
                                AccessKeyId=key_metadata['AccessKeyId'],
                                Status='Inactive'
                            )
                            keys_deactivated += 1
                        except ClientError as key_error:
                            print(f"⚠️ Failed to deactivate key for {user_name}: {key_error}")
                
                # Remove console access
                console_removed = False
                if user_info['has_console_access']:
                    try:
                        client.delete_login_profile(UserName=user_name)
                        console_removed = True
                    except ClientError as e:
                        if e.response['Error']['Code'] != 'NoSuchEntity':
                            raise
                
                disabled_users.append({
                    'user_name': user_name,
                    'keys_deactivated': keys_deactivated,
                    'console_access_removed': console_removed,
                    'inactive_days': user_info.get('days_since_key_usage', 'unknown')
                })
                
                print(f"✅ Disabled inactive user: {user_name}")
                
            except ClientError as e:
                error_msg = f"Failed to disable user {user_name}: {e}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")
        
        return {
            "success": len(disabled_users) > 0,
            "message": f"Disabled {len(disabled_users)} inactive users",
            "disabled_users": disabled_users,
            "errors": errors,
            "next_steps": [
                "Monitor for any service disruptions",
                "Users can be re-enabled by creating new login profiles/keys",
                "Consider deleting users after 30-day monitoring period"
            ]
        }
    
    def _remove_user_permissions(self, client):
        """Remove all permissions but keep user account."""
        # Implementation for removing permissions
        return {"success": False, "message": "Permission removal not implemented yet"}
    
    def _delete_users(self, client):
        """Fully delete inactive users."""
        # Implementation for deleting users (requires careful cleanup)
        return {"success": False, "message": "User deletion requires manual implementation for safety"}
