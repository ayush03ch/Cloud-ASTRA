# agents/vpc_agent/llm_fallback.py

class LLMFallback:
    def suggest_fix(self, issue, intent=None, vpc_id=None):
        return {
            "service": "vpc",
            "issue": issue,
            "fix": {
                "action": "manual_review",
                "params": {},
                "suggestion": (
                    f"Review VPC {vpc_id} and apply recommended security settings: "
                    "flow logs, default VPC removal, default SG rules, NACL restrictions."
                ),
            },
            "auto_safe": False,
        }
