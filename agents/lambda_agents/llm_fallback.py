# agents/lambda_agents/llm_fallback.py

class LLMFallback:
    def suggest_fix(self, issue, intent=None, function_name=None):
        """
        Enhanced LLM fallback with intent context.
        
        Args:
            issue: The detected issue
            intent: User's detected intent (e.g., "api_endpoint", "scheduled_task")
            function_name: Name of the Lambda function for context
        """
        # Intent-aware fix suggestions
        if intent == "api_endpoint":
            return {
                "service": "lambda",
                "issue": f"API endpoint issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Check CloudWatch Logs for errors, verify environment variables are encrypted, and ensure timeout is sufficient"
                },
                "auto_safe": False,
                "intent_context": f"Function '{function_name}' appears to be an API endpoint"
            }
        elif intent == "scheduled_task":
            return {
                "service": "lambda",
                "issue": f"Scheduled task issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Verify CloudWatch Events/EventBridge trigger, check logs, and ensure timeout is sufficient for task duration"
                },
                "auto_safe": False,
                "intent_context": f"Function '{function_name}' appears to be a scheduled task"
            }
        elif intent in ["event_processor", "stream_processor"]:
            return {
                "service": "lambda",
                "issue": f"Event processing issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Check event source mapping configuration, verify batch size, and ensure error handling is implemented"
                },
                "auto_safe": False,
                "intent_context": f"Function '{function_name}' appears to be an {intent}"
            }
        elif intent == "notification_handler":
            return {
                "service": "lambda",
                "issue": f"Notification handler issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Verify credentials are securely stored, check timeout for external API calls, and implement retry logic"
                },
                "auto_safe": False,
                "intent_context": f"Function '{function_name}' appears to be a notification handler"
            }
        elif intent == "data_transformation":
            return {
                "service": "lambda",
                "issue": f"Data transformation issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Allocate more memory if needed, implement proper error handling, and log transformation steps"
                },
                "auto_safe": False,
                "intent_context": f"Function '{function_name}' appears to be for data transformation"
            }
        else:
            # Fallback for unknown intent
            return {
                "service": "lambda",
                "issue": issue,
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Manual review required - verify CloudWatch Logs and function configuration"
                },
                "auto_safe": False,
                "intent_context": f"Function '{function_name}' intent is unclear"
            }
