# agents/s3_agent/rules/website_hosting_rule.py

import json

class WebsiteHostingRule:
    """
    Intent-aware rule for S3 static website hosting.
    Only triggers when intent is WEBSITE_HOSTING and configuration is incomplete.
    """
    id = "s3_website_hosting"
    detection = "Static website hosting misconfiguration"
    auto_safe = True

    def check(self, client, bucket_name):
        """
        Legacy check method - always returns False to avoid conflicts.
        Use check_with_intent instead.
        """
        return False

    def check_with_intent(self, client, bucket_name, intent, recommendations):
        """
        Intent-aware check - only applies to website hosting buckets.
        """
        from agents.s3_agent.intent_detector import S3Intent
        
        # Only check buckets with website hosting intent
        if intent != S3Intent.WEBSITE_HOSTING:
            return False
            
        print(f"🌐 Checking website hosting configuration for: {bucket_name}")
        
        # Check if website hosting is properly configured
        website_issues = []
        
        # 1. Check if website hosting is enabled
        if not self._is_website_hosting_enabled(client, bucket_name):
            website_issues.append("Website hosting not enabled")
        
        # 2. Check if objects are publicly accessible
        if not self._are_objects_publicly_readable(client, bucket_name):
            website_issues.append("Objects not publicly readable")
            
        # 3. Check for required HTML files
        if not self._has_required_website_files(client, bucket_name):
            website_issues.append("Missing required website files (index.html)")
            
        if website_issues:
            print(f"🚨 Website hosting issues found: {website_issues}")
            return True
            
        print(f"✅ Website hosting properly configured")
        return False

    def _is_website_hosting_enabled(self, client, bucket_name):
        """Check if static website hosting is enabled."""
        try:
            client.get_bucket_website(Bucket=bucket_name)
            return True
        except Exception as e:
            if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'NoSuchWebsiteConfiguration':
                return False
            return False

    def _are_objects_publicly_readable(self, client, bucket_name):
        """Check if objects can be publicly read."""
        try:
            response = client.get_bucket_policy(Bucket=bucket_name)
            policy = json.loads(response['Policy'])
            
            for statement in policy.get('Statement', []):
                if (statement.get('Effect') == 'Allow' and
                    statement.get('Principal') == '*' and
                    's3:GetObject' in statement.get('Action', [])):
                    return True
            return False
        except Exception as e:
            if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'NoSuchBucketPolicy':
                return False
            return False

    def _has_required_website_files(self, client, bucket_name):
        """Check if bucket has required website files."""
        try:
            response = client.list_objects_v2(Bucket=bucket_name, MaxKeys=100)
            objects = response.get('Contents', [])
            
            file_keys = [obj['Key'].lower() for obj in objects]
            
            # Check for index file
            has_index = any(key in ['index.html', 'index.htm'] for key in file_keys)
            
            return has_index
        except:
            return False

    def fix(self, client, bucket_name):
        """
        Fix website hosting configuration by:
        1. Enabling website hosting
        2. Adding public read policy for objects
        3. Configuring Public Access Block appropriately
        """
        try:
            print(f"🔧 Fixing website hosting for: {bucket_name}")
            
            # 1. Enable website hosting
            client.put_bucket_website(
                Bucket=bucket_name,
                WebsiteConfiguration={
                    'IndexDocument': {'Suffix': 'index.html'},
                    'ErrorDocument': {'Key': 'error.html'}
                }
            )
            print(f"✅ Enabled website hosting")
            
            # 2. Create public read policy for objects
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{bucket_name}/*"
                    }
                ]
            }
            
            client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(policy)
            )
            print(f"✅ Added public read policy for objects")
            
            # 3. Configure Public Access Block for website hosting
            client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,        # Block public ACLs (good security)
                    'IgnorePublicAcls': True,       # Ignore public ACLs (good security)
                    'BlockPublicPolicy': False,     # Allow public policy (needed for website)
                    'RestrictPublicBuckets': False  # Allow this specific public policy
                }
            )
            print(f"✅ Configured Public Access Block for website hosting")
            
            print(f"🌐 Website hosting successfully configured for: {bucket_name}")
            
        except Exception as e:
            print(f"❌ Error fixing website hosting: {e}")
            raise