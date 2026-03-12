# agents/s3_agent/rules/encryption_rule.py

class EncryptionRule:
    id = "s3_unencrypted_bucket"
    detection = "Bucket does not have default encryption"
    auto_safe = True
    
    def __init__(self):
        self.fix_instructions = [
            " FREE: Enable AES-256 server-side encryption (no additional cost)",
            "Set default encryption for all new objects",
            "Apply bucket key for cost optimization (recommended)"
        ]
        self.can_auto_fix = True
        self.fix_type = "enable_encryption"

    def check(self, client, bucket_name):
        """Check if bucket has default encryption enabled."""
        try:
            client.get_bucket_encryption(Bucket=bucket_name)
            return False  # Encryption exists
        except client.exceptions.ClientError as e:
            if "ServerSideEncryptionConfigurationNotFoundError" in str(e):
                print(f" Bucket {bucket_name} has no default encryption")
                return True
            raise

    def fix(self, client, bucket_name):
        """Enable AES-256 default encryption."""
        print(f"🔒 Enabling encryption for bucket: {bucket_name}")
        client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        },
                        "BucketKeyEnabled": True
                    }
                ]
            }
        )
        print(f" Successfully enabled encryption for bucket: {bucket_name}")
