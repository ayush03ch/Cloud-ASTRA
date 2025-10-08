# fixer_agent/executor.py

import boto3
import logging
import time
from .config import MAX_RETRIES, TIMEOUT

class Executor:
    """
    Executes fixes for findings. Currently supports only S3.
    """
    def __init__(self, creds: dict):
        self.logger = logging.getLogger("fixer_agent")
        try:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=creds.get("aws_access_key_id"),
                aws_secret_access_key=creds.get("aws_secret_access_key"),
                aws_session_token=creds.get("aws_session_token"),
                region_name=creds.get("region")
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None


    def run(self, finding: dict) -> bool:
        """
        Execute fix based on finding definition.
        finding = {
            "service": "s3",
            "resource": "bucket-name",
            "issue": "Bucket is public",
            "fix": {
                "action": "put_bucket_acl",
                "params": {"Bucket": "bucket-name", "ACL": "private"}
            },
            "auto_safe": True
        }
        """
        service = finding.get("service")
        fix = finding.get("fix", {})
        action = fix.get("action")
        params = fix.get("params", {})

        if service != "s3":
            self.logger.warning(f"Unsupported service: {service}")
            return False

        if not self.s3_client:
            self.logger.error("S3 client not initialized. Skipping fix.")
            return False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Handle custom actions
                if action == "fix_public_access":
                    self._fix_public_access(finding["resource"])
                elif action == "fix_website_hosting":
                    self._fix_website_hosting(finding["resource"])
                elif action == "rule_based_fix":
                    # Let the original rule handle the fix
                    self._apply_rule_fix(finding)
                elif action == "manual_review":
                    self.logger.info(f"Fix requires manual review: {finding}")
                    return False  # Don't auto-apply manual reviews
                else:
                    # Try to call boto3 method directly
                    method = getattr(self.s3_client, action)
                    method(**params)
                
                self.logger.info(f"[SUCCESS] Applied fix: {finding}")
                return True
            except Exception as e:
                self.logger.error(
                    f"Attempt {attempt}/{MAX_RETRIES} failed for {finding['resource']}: {e}"
                )
                time.sleep(1)  # small backoff

        return False
    
    def _apply_rule_fix(self, finding):
        """Apply fix using the original rule's fix method."""
        rule_id = finding.get("fix", {}).get("params", {}).get("rule_id")
        bucket_name = finding.get("fix", {}).get("params", {}).get("bucket_name")
        
        # If bucket_name is empty, get it from the finding resource
        if not bucket_name:
            bucket_name = finding.get("resource")
        
        if not rule_id or not bucket_name:
            raise Exception(f"Missing rule_id ({rule_id}) or bucket_name ({bucket_name}) for rule-based fix")
        
        # Import and instantiate the rule
        if rule_id == "s3_unencrypted_bucket":
            from agents.s3_agent.rules.encryption_rule import EncryptionRule
            rule = EncryptionRule()
            rule.fix(self.s3_client, bucket_name)
        elif rule_id == "s3_public_access_block":
            from agents.s3_agent.rules.public_access_rule import PublicAccessRule
            rule = PublicAccessRule()
            rule.fix(self.s3_client, bucket_name)
        elif rule_id == "s3_website_hosting":
            from agents.s3_agent.rules.website_hosting_rule import WebsiteHostingRule
            rule = WebsiteHostingRule()
            rule.fix(self.s3_client, bucket_name)
        elif rule_id == "s3_intent_conversion":
            from agents.s3_agent.rules.intent_conversion_rule import IntentConversionRule
            rule = IntentConversionRule()
            rule.fix(self.s3_client, bucket_name)
        else:
            raise Exception(f"Unknown rule_id for auto-fix: {rule_id}")
    
    def _fix_public_access(self, bucket_name):
        """Fix public access by enabling Public Access Block and making ACL private."""
        success_count = 0
        errors = []
        
        try:
            # Step 1: Enable Public Access Block (most important)
            self.s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            success_count += 1
            self.logger.info(f"✅ Enabled Public Access Block for {bucket_name}")
        except Exception as e:
            errors.append(f"Public Access Block: {e}")
            
        try:
            # Step 2: Try to remove any public bucket policy
            self.s3_client.delete_bucket_policy(Bucket=bucket_name)
            success_count += 1
            self.logger.info(f"✅ Removed bucket policy for {bucket_name}")
        except Exception as e:
            if "NoSuchBucketPolicy" not in str(e):
                errors.append(f"Policy removal: {e}")
        
        try:
            # Step 3: Try to make ACL private (may fail if ACLs disabled)
            self.s3_client.put_bucket_acl(Bucket=bucket_name, ACL="private")
            success_count += 1
            self.logger.info(f"✅ Set ACL to private for {bucket_name}")
        except Exception as e:
            if "AccessControlListNotSupported" in str(e):
                self.logger.info(f"ℹ️ Bucket {bucket_name} has ACLs disabled (this is good for security)")
            else:
                errors.append(f"ACL setting: {e}")
        
        # Consider successful if at least Public Access Block was enabled
        if success_count > 0:
            if errors:
                self.logger.warning(f"Partial success for {bucket_name}. Errors: {errors}")
            return  # Success
        else:
            # All steps failed
            raise Exception(f"All fix attempts failed: {errors}")
            
    def fix_public_access_directly(self, bucket_name):
        """Directly apply public access block fix."""
        try:
            self._fix_public_access(bucket_name)
            self.logger.info(f"✅ Successfully applied public access block to {bucket_name}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to apply public access block to {bucket_name}: {e}")
            return False
    
    def fix_index_document_directly(self, bucket_name):
        """Directly fix index document configuration."""
        try:
            print(f"🔧 Starting index document fix for {bucket_name}")
            
            # Get current website configuration
            try:
                website_config = self.s3_client.get_bucket_website(Bucket=bucket_name)
                current_index = website_config.get('IndexDocument', {}).get('Suffix', '')
                print(f"📋 Current index document: '{current_index}'")
            except Exception as e:
                print(f"❌ Could not get current website config: {e}")
                website_config = {}
                current_index = ""
            
            # List objects to find HTML files
            response = self.s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=100)
            objects = response.get('Contents', [])
            
            # Find HTML files
            html_files = []
            for obj in objects:
                key = obj['Key']
                if key.lower().endswith(('.html', '.htm')):
                    html_files.append(key)  # Keep original case
            
            print(f"📄 Found HTML files: {html_files}")
            
            # Determine best index file
            suggested_index = "index.html"  # default
            if html_files:
                # Prefer common index file names
                for common_name in ['index.html', 'home.html', 'main.html', 'default.html']:
                    if any(f.lower() == common_name for f in html_files):
                        suggested_index = next(f for f in html_files if f.lower() == common_name)
                        break
                else:
                    # Use first HTML file found
                    suggested_index = html_files[0]
            
            print(f"💡 Suggested index document: '{suggested_index}'")
            
            # Update website configuration with correct index
            print(f"🔄 Updating website configuration...")
            self.s3_client.put_bucket_website(
                Bucket=bucket_name,
                WebsiteConfiguration={
                    'IndexDocument': {'Suffix': suggested_index},
                    'ErrorDocument': {'Key': 'error.html'}
                }
            )
            
            print(f"✅ Successfully updated index document from '{current_index}' to '{suggested_index}' for {bucket_name}")
            
            # Also apply proper website hosting configuration
            self._fix_website_hosting(bucket_name)
            
            self.logger.info(f"✅ Successfully updated index document to {suggested_index} for {bucket_name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to fix index document for {bucket_name}: {e}")
            self.logger.error(f"❌ Failed to fix index document for {bucket_name}: {e}")
            return False
    
    def disable_website_hosting_directly(self, bucket_name):
        """Directly disable website hosting and secure bucket."""
        try:
            # Step 1: Remove website configuration
            try:
                self.s3_client.delete_bucket_website(Bucket=bucket_name)
                self.logger.info(f"✅ Removed website hosting configuration for {bucket_name}")
            except Exception as e:
                if "NoSuchWebsiteConfiguration" not in str(e):
                    self.logger.warning(f"⚠️ Could not remove website config for {bucket_name}: {e}")
            
            # Step 2: Apply data storage security (public access block + private policy)
            self._fix_public_access(bucket_name)
            
            self.logger.info(f"✅ Successfully disabled website hosting and secured {bucket_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to disable website hosting for {bucket_name}: {e}")
            return False
    
    def enable_website_hosting_directly(self, bucket_name):
        """Directly enable website hosting with HTML file detection."""
        try:
            # List objects to find HTML files
            response = self.s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=100)
            objects = response.get('Contents', [])
            
            # Find HTML files
            html_files = []
            for obj in objects:
                key = obj['Key'].lower()
                if key.endswith(('.html', '.htm')):
                    html_files.append(obj['Key'])
            
            # Determine index file
            index_file = "index.html"  # default
            if html_files:
                # Prefer common names
                for common_name in ['index.html', 'home.html', 'main.html', 'default.html']:
                    if any(f.lower() == common_name for f in html_files):
                        index_file = next(f for f in html_files if f.lower() == common_name)
                        break
                else:
                    index_file = html_files[0]
            
            # Enable website hosting
            self.s3_client.put_bucket_website(
                Bucket=bucket_name,
                WebsiteConfiguration={
                    'IndexDocument': {'Suffix': index_file},
                    'ErrorDocument': {'Key': 'error.html'}
                }
            )
            
            # Configure public access for website
            self._fix_website_hosting(bucket_name)
            
            self.logger.info(f"✅ Successfully enabled website hosting for {bucket_name} with index: {index_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to enable website hosting for {bucket_name}: {e}")
            return False
    
    def enable_public_access_directly(self, bucket_name):
        """Directly enable public access for website hosting."""
        try:
            # Apply website hosting configuration (which includes public access)
            self._fix_website_hosting(bucket_name)
            
            self.logger.info(f"✅ Successfully enabled public access for website {bucket_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to enable public access for {bucket_name}: {e}")
            return False
            
    def _fix_website_hosting(self, bucket_name):
        """Fix website hosting configuration using the proper rule."""
        try:
            # Use the website hosting rule which has proper analysis logic
            from agents.s3_agent.rules.website_hosting_rule import WebsiteHostingRule
            rule = WebsiteHostingRule()
            rule.fix(self.s3_client, bucket_name)
            self.logger.info(f"✅ Successfully applied website hosting fix using rule for {bucket_name}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to fix website hosting for {bucket_name}: {e}")
            raise
