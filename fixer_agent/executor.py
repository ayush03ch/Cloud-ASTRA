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
                # aws_session_token=creds.get("aws_session_token"),
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
