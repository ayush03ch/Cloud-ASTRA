# agents/route53_agent/llm_fallback.py

class LLMFallback:
    """
    Provides LLM-based security recommendations when rules don't apply.
    This is a simple fallback; the main LLM analysis happens in Tier 3.
    """

    def suggest_fix(self, issue: str, intent: str, zone_name: str) -> str:
        """
        Suggest a fix using LLM or return generic recommendation.
        
        Args:
            issue: Description of the security issue
            intent: Detected intent of the hosted zone
            zone_name: Name of the hosted zone
            
        Returns:
            Fix suggestion string
        """
        # Generic recommendations based on intent
        intent_fixes = {
            "public_website": "Consider enabling DNSSEC, adding CAA records, and configuring health checks",
            "api_service": "Enable DNSSEC, configure health checks, and ensure proper SSL/TLS configuration",
            "email_domain": "Verify SPF, DKIM, and DMARC records are properly configured",
            "internal_service": "Ensure zone is private and VPC associations are correct",
            "cdn_distribution": "Use ALIAS records and enable DNSSEC for content integrity"
        }
        
        return intent_fixes.get(intent, "Review Route53 security best practices and enable DNSSEC")
