# agents/s3_agent/rules/versioning_rule.py

class VersioningRule:
    id = "s3_versioning_disabled"
    detection = "Bucket versioning is not enabled"
    auto_safe = False  # Manual only - versioning can incur storage costs
    
    def __init__(self):
        self.fix_instructions = [
            "⚠️ COST CONSIDERATION: Versioning stores multiple copies of objects and may increase storage costs",
            "Enable S3 bucket versioning for data protection (optional)",
            "Protects against accidental deletions and modifications",
            "Maintains object history for compliance requirements",
            "Consider lifecycle policies to manage old versions and costs"
        ]
        self.can_auto_fix = False  # Never auto-fix due to cost implications
        self.fix_type = "enable_versioning_manual"

    def check(self, client, bucket_name):
        """Check if bucket has versioning enabled."""
        try:
            response = client.get_bucket_versioning(Bucket=bucket_name)
            status = response.get('Status', 'Disabled')
            
            if status != 'Enabled':
                print(f"❌ Bucket {bucket_name} versioning is {status}")
                return True
                
            return False
        except Exception as e:
            print(f"❌ Error checking versioning for {bucket_name}: {e}")
            return False

    def check_with_intent(self, client, bucket_name, intent, recommendations):
        """Intent-aware versioning check."""
        from agents.s3_agent.intent_detector import S3Intent
        
        # For data storage and backup, versioning is important
        if intent in [S3Intent.DATA_STORAGE, S3Intent.BACKUP_STORAGE, S3Intent.DATA_ARCHIVAL]:
            return self.check(client, bucket_name)
        
        # For website hosting, versioning is optional but good practice
        if intent == S3Intent.WEBSITE_HOSTING:
            if self.check(client, bucket_name):
                # Lower priority for websites
                self.fix_instructions = [
                    "Consider enabling versioning for website hosting",
                    "Protects against accidental file overwrites",
                    "Allows easy rollback of website changes"
                ]
                return True
                
        return False

    def fix(self, client, bucket_name):
        """Enable bucket versioning."""
        print(f"📦 Enabling versioning for bucket: {bucket_name}")
        client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={
                'Status': 'Enabled'
            }
        )
        print(f"✅ Successfully enabled versioning for bucket: {bucket_name}")