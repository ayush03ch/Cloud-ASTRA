# agents/cloudfront_agent/rules/https_redirect_rule.py

class HttpsRedirectRule:
    id = "cloudfront_http_not_redirected"
    detection = "CloudFront distribution does not redirect HTTP to HTTPS"
    severity = "high"
    auto_safe = True
    can_auto_fix = True
    fix_type = "enforce_https"

    def __init__(self):
        self.fix_instructions = [
            "1. Open the CloudFront console and select the distribution",
            "2. Go to 'Behaviors' and edit the default cache behavior",
            "3. Under 'Viewer Protocol Policy', select 'Redirect HTTP to HTTPS'",
            "4. Save and wait for the distribution to deploy (~15 min)",
        ]

    def check(self, client, distribution_id, dist_info):
        try:
            response = client.get_distribution_config(Id=distribution_id)
            behavior = response['DistributionConfig'].get('DefaultCacheBehavior', {})
            policy = behavior.get('ViewerProtocolPolicy', '')
            return policy not in ('redirect-to-https', 'https-only')
        except Exception as e:
            print(f"[HttpsRedirectRule] Error checking {distribution_id}: {e}")
            return False

    def fix(self, client, distribution_id, dist_info):
        print(f"⚠️ Manual fix required: enable HTTPS redirect on distribution {distribution_id}")
        return False
