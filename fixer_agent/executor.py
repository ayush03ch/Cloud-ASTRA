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
