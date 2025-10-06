#  agents/s3_agent/rules/public_access_rule.py

import json

class PublicAccessRule:
    id = "s3_public_access_block"
    detection = "Bucket allows public read access"
    auto_safe = True
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = True
        self.fix_type = "public_access_block"
    
    def check_with_intent(self, client, bucket_name, intent, recommendations):
        """Intent-aware public access check."""
        from agents.s3_agent.intent_detector import S3Intent
        
        # For website hosting buckets, public access is expected
        if intent == S3Intent.WEBSITE_HOSTING:
            print(f"ℹ️ Skipping public access check for website bucket: {bucket_name}")
            return False
        
        # For all other intents, check for unwanted public access
        is_public = self.check(client, bucket_name)
        
        if is_public:
            # Set detailed fix instructions based on intent
            if intent == S3Intent.DATA_STORAGE:
                self.fix_instructions = [
                    "Enable Public Access Block to prevent all public access",
                    "Remove any public bucket policies",
                    "Set bucket ACL to private",
                    "Consider enabling bucket encryption for sensitive data"
                ]
            else:
                self.fix_instructions = [
                    "Enable Public Access Block to prevent public access",
                    "Remove any public bucket policies", 
                    "Set bucket ACL to private",
                    "Verify access is restricted to authorized users only"
                ]
            
            self.can_auto_fix = True
            self.fix_type = "public_access_block"
            
            print(f"🚨 Non-website bucket {bucket_name} has public access - this should be fixed")
        
        return is_public

    def check(self, client, bucket_name):
        """Check if bucket is publicly accessible via ACL or policy."""
        try:
            print(f"🔍 Checking bucket: {bucket_name}")

            # Check 1: Bucket ACL
            if self._check_public_acl(client, bucket_name):
                return True

            # Check 2: Bucket Policy
            if self._check_public_policy(client, bucket_name):
                return True

            # Check 3: Public Access Block settings
            if self._check_public_access_block(client, bucket_name):
                return True

            return False

        except Exception as e:
            print(f"❌ Error checking bucket {bucket_name}: {e}")
            return False

    def _check_public_policy(self, client, bucket_name):
        """Check if bucket policy allows public access."""
        try:
            response = client.get_bucket_policy(Bucket=bucket_name)
            policy = json.loads(response['Policy'])

            print(f"📋 Bucket Policy: {policy}")

            for statement in policy.get('Statement', []):
                principal = statement.get('Principal')
                effect = statement.get('Effect')

                # Check for public principal with Allow effect
                if effect == 'Allow':
                    if principal == '*' or principal == {"AWS": "*"}:
                        print(f"🚨 Found public bucket policy")
                        return True

            return False
        except Exception as e:
            # Check if it's a NoSuchBucketPolicy error by examining the error code
            if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'NoSuchBucketPolicy':
                print("ℹ️ No bucket policy found")
                return False
            else:
                print(f"❌ Error checking policy: {e}")
                return False

    def _check_public_acl(self, client, bucket_name):
        """Check if bucket ACL allows public access."""
        try:
            acl = client.get_bucket_acl(Bucket=bucket_name)
            for grant in acl["Grants"]:
                grantee = grant.get("Grantee", {})
                permission = grant.get("Permission")
                
                if grantee.get("Type") == "Group" and permission in ["READ", "READ_ACP", "FULL_CONTROL"]:
                    uri = grantee.get("URI", "")
                    if "AllUsers" in uri or "AuthenticatedUsers" in uri:
                        print(f"🚨 Found public ACL: {permission} to {uri}")
                        return True
            return False
        except:
            return False

    def _check_public_access_block(self, client, bucket_name):
        """Check if Public Access Block is disabled."""
        try:
            response = client.get_public_access_block(Bucket=bucket_name)
            config = response["PublicAccessBlockConfiguration"]
            
            print(f"📋 Public Access Block Config: {config}")
            
            # If any of these are False, bucket could be public
            if not all([
                config.get("BlockPublicAcls", True),
                config.get("IgnorePublicAcls", True),
                config.get("BlockPublicPolicy", True),
                config.get("RestrictPublicBuckets", True)
            ]):
                print(f"🚨 Public Access Block not fully enabled")
                return True
            return False
        except Exception as e:
            # Check if it's NoSuchPublicAccessBlockConfiguration
            if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'NoSuchPublicAccessBlockConfiguration':
                print(f"⚠️ No Public Access Block configured - potentially public")
                return True
            elif hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'AccessDenied':
                print(f"⚠️ Cannot check Public Access Block (no permissions) - assuming potentially public")
                return True  # Conservative approach: if we can't check, assume it might be public
            else:
                print(f"❌ Error checking PAB: {e}")
                return False

    def fix(self, client, bucket_name):
        """Fix by removing public policy and enabling Public Access Block."""
        try:
            # Remove bucket policy if it exists
            try:
                client.delete_bucket_policy(Bucket=bucket_name)
                print(f"🗑️ Removed public bucket policy")
            except Exception as e:
                if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'NoSuchBucketPolicy':
                    print("ℹ️ No bucket policy to remove")
                else:
                    print(f"⚠️ Error removing policy: {e}")
                
            # Enable Public Access Block
            client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            
            # Make ACL private
            client.put_bucket_acl(Bucket=bucket_name, ACL="private")
            print(f"🔒 Secured bucket {bucket_name}")
            
        except Exception as e:
            print(f"❌ Error fixing bucket {bucket_name}: {e}")
            raise