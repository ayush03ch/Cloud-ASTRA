# agents/s3_agent/llm_fallback.py

class LLMFallback:
    def suggest_fix(self, issue, intent=None, bucket_name=None):
        """
        Enhanced LLM fallback with intent context.
        
        Args:
            issue: The detected issue
            intent: User's detected intent (e.g., "website_hosting", "data_storage")
            bucket_name: Name of the bucket for context
        """
        # Intent-aware fix suggestions
        if intent == "website_hosting":
            return {
                "service": "s3",
                "issue": f"Website hosting issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Check if website hosting is enabled, objects are publicly readable, and index.html exists"
                },
                "auto_safe": False,
                "intent_context": f"Bucket '{bucket_name}' appears to be for website hosting"
            }
        elif intent in ["data_storage", "data_archival"]:
            return {
                "service": "s3",
                "issue": f"Data storage issue: {issue}",
                "fix": {
                    "action": "manual_review", 
                    "params": {},
                    "suggestion": "Ensure encryption is enabled, public access is blocked, and appropriate storage class is used"
                },
                "auto_safe": False,
                "intent_context": f"Bucket '{bucket_name}' appears to be for {intent}"
            }
        else:
            # Fallback for unknown intent
            return {
                "service": "s3",
                "issue": issue,
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Manual review required - intent unclear"
                },
                "auto_safe": False,
                "intent_context": f"Bucket '{bucket_name}' intent is unclear"
            }
