# agents/s3_agent/rules/encryption_rule.py

class EncryptionRule:
    id = "s3_unencrypted_bucket"
    detection = "Bucket does not have default encryption"
    auto_safe = True

    def check(self, client, bucket_name):
        """Check if bucket has default encryption enabled."""
        try:
            client.get_bucket_encryption(Bucket=bucket_name)
            return False  # Encryption exists
        except client.exceptions.ClientError as e:
            if "ServerSideEncryptionConfigurationNotFoundError" in str(e):
                return True
            raise

    def fix(self, client, bucket_name):
        """Enable AES-256 default encryption."""
        client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }
        )
