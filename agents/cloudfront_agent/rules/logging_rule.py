# agents/cloudfront_agent/rules/logging_rule.py

class LoggingRule:
    id = "cloudfront_logging_disabled"
    detection = "CloudFront distribution does not have access logging enabled"
    severity = "medium"
    auto_safe = False
    can_auto_fix = False
    fix_type = "enable_logging"

    def __init__(self):
        self.fix_instructions = [
            "1. Create or identify an S3 bucket for CloudFront access logs",
            "2. Ensure the bucket grants write access to the CloudFront logging service",
            "3. In CloudFront distribution settings, go to 'General' → 'Standard Logging'",
            "4. Enable standard logging and specify the S3 bucket and optional prefix",
            "5. Save changes and wait for deployment",
        ]

    def check(self, client, distribution_id, dist_info):
        try:
            response = client.get_distribution_config(Id=distribution_id)
            logging_config = response['DistributionConfig'].get('Logging', {})
            return not logging_config.get('Enabled', False)
        except Exception as e:
            print(f"[LoggingRule] Error checking {distribution_id}: {e}")
            return False

    def fix(self, client, distribution_id, dist_info):
        print(f"⚠️ Manual fix required: enable access logging on distribution {distribution_id}")
        return False
