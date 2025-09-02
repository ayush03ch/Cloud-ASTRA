#  agents/s3_agent/rules/public_access_rule.py

class PublicAccessRule:
    id = "s3_public_access_block"
    detection = "Bucket allows public read access"
    auto_safe = True

    def check(self, client, bucket_name):
        """Check if the bucket ACL grants public READ access."""
        acl = client.get_bucket_acl(Bucket=bucket_name)
        for grant in acl["Grants"]:
            if grant["Permission"] == "READ" and "AllUsers" in str(grant["Grantee"]):
                return True
        return False

    def fix(self, client, bucket_name):
        """Fix by making ACL private."""
        client.put_bucket_acl(Bucket=bucket_name, ACL="private")
