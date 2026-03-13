# agents/apigateway_agent/llm_fallback.py

class LLMFallback:
    """Fallback fix suggestions for API Gateway issues."""

    def suggest_fix(self, issue: str, intent: str, api_name: str) -> str:
        intent_fixes = {
            "public_api":    "Enable WAF, enforce TLS 1.2+, add usage plans, and enable access logging",
            "internal_api":  "Restrict via resource policies or VPC endpoints, enable CloudWatch logging",
            "partner_api":   "Enforce API keys/usage plans, enable mutual TLS, add throttling",
            "mobile_backend":"Enable Cognito authorizer, enforce HTTPS, add WAF rules",
        }
        return intent_fixes.get(intent, "Review API Gateway security best practices and enable access logging")
