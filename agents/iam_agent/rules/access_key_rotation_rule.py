# agents/iam_agent/rules/access_key_rotation_rule.py

import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import json


class AccessKeyRotationRule:
    """
    Rule to detect and remediate old IAM access keys that need rotation
    for security compliance and best practices.
    """
    
    id = "iam_access_key_rotation"
    detection = "IAM access keys are old and need rotation"
    auto_safe = False  # Key rotation requires careful coordination
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = False
        self.fix_type = None
        self.old_keys = None
        self.rotation_threshold_days = 90
        self.warning_threshold_days = 75
    
    def check(self, client, user_name=None, max_key_age_days=90):
        """Check for old access keys that need rotation."""
        self.rotation_threshold_days = max_key_age_days
        self.warning_threshold_days = max_key_age_days - 15
        
        try:
            old_keys = []
            
            if user_name:
                # Check specific user
                user_keys = self._check_user_access_keys(client, user_name)
                old_keys.extend(user_keys)
            else:
                # Check all users in account
                users = client.list_users()
                for user in users.get('Users', [])[:50]:  # Limit to first 50 users
                    user_keys = self._check_user_access_keys(client, user['UserName'])
                    old_keys.extend(user_keys)
            
            if old_keys:
                self.old_keys = old_keys
                self._set_fix_instructions(old_keys)
                print(f"🔴 Found {len(old_keys)} old access keys requiring rotation")
                return True
            
            print(f"✅ All access keys are within {max_key_age_days} day rotation policy")
            return False
            
        except ClientError as e:
            print(f"❌ Error checking access key rotation: {e}")
            return False
    
    def _check_user_access_keys(self, client, user_name):
        """Check access keys for a specific user."""
        old_keys = []
        
        try:
            # Get user's access keys
            access_keys = client.list_access_keys(UserName=user_name)
            
            for key_metadata in access_keys.get('AccessKeyMetadata', []):
                access_key_id = key_metadata['AccessKeyId']
                creation_date = key_metadata['CreateDate']
                status = key_metadata['Status']
                
                # Calculate key age
                if hasattr(creation_date, 'replace'):
                    creation_date = creation_date.replace(tzinfo=None)
                
                key_age_days = (datetime.utcnow() - creation_date).days
                
                # Get last used information
                last_used_info = self._get_key_last_used(client, access_key_id)
                
                # Determine if key needs rotation
                severity = self._determine_key_severity(key_age_days, last_used_info, status)
                
                if severity:
                    old_keys.append({
                        'user_name': user_name,
                        'access_key_id': access_key_id,
                        'age_days': key_age_days,
                        'status': status,
                        'creation_date': creation_date.isoformat(),
                        'last_used': last_used_info,
                        'severity': severity,
                        'recommendation': self._get_key_recommendation(key_age_days, last_used_info, status)
                    })
                    
        except ClientError as e:
            print(f"⚠️ Error checking access keys for user {user_name}: {e}")
        
        return old_keys
    
    def _get_key_last_used(self, client, access_key_id):
        """Get last used information for an access key."""
        try:
            response = client.get_access_key_last_used(AccessKeyId=access_key_id)
            last_used_data = response.get('AccessKeyLastUsed', {})
            
            last_used_date = last_used_data.get('LastUsedDate')
            service_name = last_used_data.get('ServiceName', 'Unknown')
            region = last_used_data.get('Region', 'Unknown')
            
            if last_used_date:
                if hasattr(last_used_date, 'replace'):
                    last_used_date = last_used_date.replace(tzinfo=None)
                days_since_last_use = (datetime.utcnow() - last_used_date).days
            else:
                days_since_last_use = None
            
            return {
                'last_used_date': last_used_date.isoformat() if last_used_date else None,
                'days_since_last_use': days_since_last_use,
                'service_name': service_name,
                'region': region,
                'never_used': last_used_date is None
            }
            
        except ClientError as e:
            return {
                'last_used_date': None,
                'days_since_last_use': None,
                'service_name': 'Unknown',
                'region': 'Unknown',
                'never_used': True,
                'error': str(e)
            }
    
    def _determine_key_severity(self, key_age_days, last_used_info, status):
        """Determine the severity level for a key based on age and usage."""
        if status == 'Inactive':
            return None  # Skip inactive keys
        
        # Critical: Very old keys (> threshold)
        if key_age_days > self.rotation_threshold_days:
            if last_used_info.get('never_used'):
                return 'critical'  # Old and never used
            elif last_used_info.get('days_since_last_use', 0) > 30:
                return 'high'  # Old and not used recently
            else:
                return 'high'  # Old but recently used
        
        # High: Approaching threshold
        elif key_age_days > self.warning_threshold_days:
            return 'medium'  # Warning - approaching rotation time
        
        # Check for never-used keys that are somewhat old
        elif key_age_days > 30 and last_used_info.get('never_used'):
            return 'medium'  # Unused key that's getting old
        
        return None  # Key is fine
    
    def _get_key_recommendation(self, key_age_days, last_used_info, status):
        """Get specific recommendation for a key."""
        if last_used_info.get('never_used') and key_age_days > self.rotation_threshold_days:
            return "Delete unused key (never been used)"
        elif last_used_info.get('never_used'):
            return "Consider deleting unused key or rotate if needed"
        elif key_age_days > self.rotation_threshold_days:
            return "Rotate immediately - exceeds policy"
        elif key_age_days > self.warning_threshold_days:
            return "Schedule rotation soon - approaching policy limit"
        else:
            return "Monitor usage and plan rotation"
    
    def _set_fix_instructions(self, old_keys):
        """Set instructions for rotating access keys."""
        critical_keys = [k for k in old_keys if k['severity'] == 'critical']
        high_keys = [k for k in old_keys if k['severity'] == 'high']
        medium_keys = [k for k in old_keys if k['severity'] == 'medium']
        
        self.fix_instructions = [
            f"🔑 Access Key Rotation Required",
            f"Total Keys: {len(old_keys)} | Critical: {len(critical_keys)} | High: {len(high_keys)} | Medium: {len(medium_keys)}",
            "🚨 Critical Keys (Immediate Action Required):"
        ]
        
        for key in critical_keys[:5]:  # Show first 5 critical
            last_used_str = 'Never' if key['last_used']['never_used'] else f"{key['last_used']['days_since_last_use']} days ago"
            self.fix_instructions.extend([
                f"• User: {key['user_name']} | Key: {key['access_key_id'][:8]}*** | Age: {key['age_days']} days",
                f"  Last Used: {last_used_str}",
                f"  Action: {key['recommendation']}"
            ])
        
        if len(critical_keys) > 5:
            self.fix_instructions.append(f"  ... and {len(critical_keys) - 5} more critical keys")
        
        self.fix_instructions.append("⚠️ High Priority Keys:")
        
        for key in high_keys[:3]:  # Show first 3 high priority
            self.fix_instructions.extend([
                f"• User: {key['user_name']} | Key: {key['access_key_id'][:8]}*** | Age: {key['age_days']} days",
                f"  Action: {key['recommendation']}"
            ])
        
        self.fix_instructions.extend([
            "🔧 Access Key Rotation Process:",
            "1. Create new access key for user",
            "2. Update applications/services to use new key", 
            "3. Test applications with new key",
            "4. Deactivate old key (keep for rollback)",
            "5. Monitor for errors for 24-48 hours",
            "6. Delete old key once confirmed working",
            "🔒 For Unused Keys:",
            "1. Confirm key is truly unused",
            "2. Deactivate key first (reversible)",
            "3. Monitor for any service disruptions", 
            "4. Delete key after confirmation period",
            "⚠️ Impact: Applications using old keys will stop working after rotation"
        ])
        
        # Can auto-fix only unused keys
        unused_keys = [k for k in old_keys if k['last_used']['never_used']]
        self.can_auto_fix = len(unused_keys) > 0
        self.fix_type = "deactivate_unused_keys" if unused_keys else "manual_rotation_required"
    
    def fix(self, client, auto_approve=False):
        """Fix access key rotation issues (limited to safe operations)."""
        try:
            print(f"🔧 Attempting to fix access key rotation issues...")
            
            if not self.old_keys:
                return {"success": False, "message": "No keys to process"}
            
            # Only auto-fix unused keys by deactivating them
            unused_keys = [k for k in self.old_keys if k['last_used']['never_used'] and k['age_days'] > 30]
            
            if not unused_keys:
                return {
                    "success": False,
                    "message": "No safe auto-fixes available - manual rotation required",
                    "keys_requiring_manual_rotation": len(self.old_keys),
                    "recommendation": "Use rotation process outlined in fix instructions"
                }
            
            if not auto_approve:
                return {
                    "success": False,
                    "message": "Unused key deactivation requires approval",
                    "unused_keys": len(unused_keys),
                    "action_required": "Approve deactivation of unused keys"
                }
            
            # Deactivate unused keys (safe operation)
            deactivated_keys = []
            errors = []
            
            for key in unused_keys:
                try:
                    client.update_access_key(
                        UserName=key['user_name'],
                        AccessKeyId=key['access_key_id'],  # Use actual key ID
                        Status='Inactive'
                    )
                    
                    deactivated_keys.append({
                        'user': key['user_name'],
                        'key_id': key['access_key_id'][:8] + '***',
                        'age_days': key['age_days']
                    })
                    
                    print(f"✅ Deactivated unused key for user {key['user_name']}")
                    
                except ClientError as e:
                    error_msg = f"Failed to deactivate key for {key['user_name']}: {e}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
            
            remaining_keys = len(self.old_keys) - len(deactivated_keys)
            
            result = {
                "success": len(deactivated_keys) > 0,
                "message": f"Deactivated {len(deactivated_keys)} unused keys",
                "deactivated_keys": deactivated_keys,
                "remaining_keys_need_manual_rotation": remaining_keys,
                "errors": errors
            }
            
            if remaining_keys > 0:
                result["next_steps"] = [
                    "Monitor deactivated keys for 24-48 hours",
                    "Delete deactivated keys if no issues",
                    f"Manually rotate {remaining_keys} active keys",
                    "Use proper rotation process for active keys"
                ]
            
            return result
            
        except ClientError as e:
            return {
                "success": False,
                "message": f"Error processing access keys: {e}",
                "recommendation": "Manual intervention required"
            }
    
    def check_single_key(self, client, user_name, access_key_id):
        """Check a specific access key for rotation needs."""
        try:
            # Get key metadata
            access_keys = client.list_access_keys(UserName=user_name)
            key_found = None
            
            for key_metadata in access_keys.get('AccessKeyMetadata', []):
                if key_metadata['AccessKeyId'] == access_key_id:
                    key_found = key_metadata
                    break
            
            if not key_found:
                return {"error": f"Access key {access_key_id} not found for user {user_name}"}
            
            creation_date = key_found['CreateDate']
            if hasattr(creation_date, 'replace'):
                creation_date = creation_date.replace(tzinfo=None)
            
            key_age_days = (datetime.utcnow() - creation_date).days
            last_used_info = self._get_key_last_used(client, access_key_id)
            severity = self._determine_key_severity(key_age_days, last_used_info, key_found['Status'])
            
            return {
                'access_key_id': access_key_id,
                'user_name': user_name,
                'age_days': key_age_days,
                'status': key_found['Status'],
                'last_used': last_used_info,
                'needs_rotation': severity is not None,
                'severity': severity,
                'recommendation': self._get_key_recommendation(key_age_days, last_used_info, key_found['Status'])
            }
            
        except ClientError as e:
            return {"error": f"Error checking key {access_key_id}: {e}"}
