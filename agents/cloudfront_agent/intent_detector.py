# agents/cloudfront_agent/intent_detector.py

class CloudFrontIntentDetector:
    def detect_intent(self, distribution_id, domain, client):
        """Detect the purpose of the CloudFront distribution."""
        try:
            response = client.get_distribution(Id=distribution_id)
            config = response.get('Distribution', {}).get('DistributionConfig', {})
            comment = config.get('Comment', '').lower()
            origins = config.get('Origins', {}).get('Items', [])

            if any(k in comment for k in ['api', 'backend', 'gateway']):
                return 'api_distribution'
            if any(k in comment for k in ['web', 'website', 'app', 'frontend']):
                return 'website'
            if origins:
                origin_domain = origins[0].get('DomainName', '').lower()
                if 's3' in origin_domain:
                    return 'static_assets'
                if 'execute-api' in origin_domain:
                    return 'api_distribution'
        except Exception:
            pass
        return 'general'
