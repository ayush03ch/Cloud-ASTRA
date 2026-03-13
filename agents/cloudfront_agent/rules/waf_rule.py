# agents/cloudfront_agent/rules/waf_rule.py

class WafRule:
    id = "cloudfront_no_waf"
    detection = "CloudFront distribution has no WAF WebACL attached"
    severity = "high"
    auto_safe = False
    can_auto_fix = False
    fix_type = "attach_waf"

    def __init__(self):
        self.fix_instructions = [
            "1. Create a WAF v2 WebACL in the 'Global (CloudFront)' scope",
            "2. Add AWS managed rule groups (AWSManagedRulesCommonRuleSet recommended)",
            "3. In the CloudFront distribution settings, associate the WebACL under 'Security'",
            "4. Save and wait for the distribution to deploy",
        ]

    def check(self, client, distribution_id, dist_info):
        try:
            response = client.get_distribution_config(Id=distribution_id)
            web_acl_id = response['DistributionConfig'].get('WebACLId', '')
            return not bool(web_acl_id)
        except Exception as e:
            print(f"[WafRule] Error checking {distribution_id}: {e}")
            return False

    def fix(self, client, distribution_id, dist_info):
        print(f"⚠️ Manual fix required: attach a WAF WebACL to distribution {distribution_id}")
        return False
