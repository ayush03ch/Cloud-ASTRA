# agents/cloudfront_agent/rules/tls_version_rule.py

WEAK_TLS_POLICIES = {'SSLv3', 'TLSv1', 'TLSv1_2016', 'TLSv1.1_2016'}


class TLSVersionRule:
    id = "cloudfront_weak_tls"
    detection = "CloudFront distribution uses a weak or outdated TLS security policy"
    severity = "high"
    auto_safe = True
    can_auto_fix = True
    fix_type = "update_tls_policy"

    def __init__(self):
        self.fix_instructions = [
            "1. Open the CloudFront distribution settings",
            "2. Under 'Security Policy', select 'TLSv1.2_2021' or higher",
            "3. Save and wait for deployment",
            "Recommended policy: TLSv1.2_2021",
        ]

    def check(self, client, distribution_id, dist_info):
        try:
            response = client.get_distribution_config(Id=distribution_id)
            viewer_cert = response['DistributionConfig'].get('ViewerCertificate', {})
            policy = viewer_cert.get('MinimumProtocolVersion', '')
            return policy in WEAK_TLS_POLICIES
        except Exception as e:
            print(f"[TLSVersionRule] Error checking {distribution_id}: {e}")
            return False

    def fix(self, client, distribution_id, dist_info):
        print(f"⚠️ Manual fix required: update TLS policy on distribution {distribution_id}")
        return False
