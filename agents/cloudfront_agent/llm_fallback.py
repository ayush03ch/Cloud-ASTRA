# agents/cloudfront_agent/llm_fallback.py

class LLMFallback:
    def suggest_fix(self, issue, intent=None, distribution_id=None):
        return {
            "service": "cloudfront",
            "issue": issue,
            "fix": {
                "action": "manual_review",
                "params": {},
                "suggestion": (
                    f"Review CloudFront distribution {distribution_id} and apply "
                    "recommended security settings: HTTPS redirect, WAF, logging, TLS 1.2+."
                ),
            },
            "auto_safe": False,
        }
