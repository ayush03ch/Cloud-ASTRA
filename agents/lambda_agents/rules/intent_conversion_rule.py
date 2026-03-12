# agents/lambda_agents/rules/intent_conversion_rule.py

from agents.lambda_agents.intent_detector import LambdaIntent

class IntentConversionRule:
    """
    This is not a traditional security rule.
    It converts detected intents into specific security checks.
    """
    id = "lambda_intent_conversion"
    detection = "Intent analysis for targeted security checks"
    auto_safe = False
    
    def __init__(self):
        self.fix_instructions = []
        self.can_auto_fix = False
        self.fix_type = "intent_based_analysis"

    def check(self, client, function_name):
        """
        This rule doesn't check anything directly.
        It's used internally by the agent for intent-based analysis.
        """
        return False

    def convert_intent_to_findings(self, intent: LambdaIntent, function_name: str):
        """
        Convert a detected intent into specific security concerns.
        Returns a list of additional checks to perform.
        """
        intent_findings_map = {
            LambdaIntent.API_ENDPOINT: [
                {
                    "issue": "API endpoint should have appropriate timeout",
                    "check": "timeout_between_30_300",
                    "severity": "medium"
                },
                {
                    "issue": "API endpoint should have sufficient memory",
                    "check": "memory_at_least_256",
                    "severity": "medium"
                },
                {
                    "issue": "API endpoint should log all requests",
                    "check": "logging_enabled",
                    "severity": "high"
                }
            ],
            LambdaIntent.SCHEDULED_TASK: [
                {
                    "issue": "Scheduled task should have timeout appropriate for duration",
                    "check": "timeout_appropriate",
                    "severity": "high"
                },
                {
                    "issue": "Scheduled task should have CloudWatch Logs enabled",
                    "check": "logging_enabled",
                    "severity": "high"
                },
                {
                    "issue": "Scheduled task should have error handling",
                    "check": "error_handling_configured",
                    "severity": "medium"
                }
            ],
            LambdaIntent.EVENT_PROCESSOR: [
                {
                    "issue": "Event processor should have error handling",
                    "check": "error_handling",
                    "severity": "high"
                },
                {
                    "issue": "Event processor should have DLQ configured",
                    "check": "dlq_configured",
                    "severity": "medium"
                },
                {
                    "issue": "Event processor should log all events",
                    "check": "logging_enabled",
                    "severity": "high"
                }
            ],
            LambdaIntent.STREAM_PROCESSOR: [
                {
                    "issue": "Stream processor should have batch window optimized",
                    "check": "batch_window_optimized",
                    "severity": "medium"
                },
                {
                    "issue": "Stream processor should handle parallelization",
                    "check": "parallelization_configured",
                    "severity": "medium"
                },
                {
                    "issue": "Stream processor should have DLQ for failed records",
                    "check": "dlq_configured",
                    "severity": "high"
                }
            ],
            LambdaIntent.NOTIFICATION_HANDLER: [
                {
                    "issue": "Notification handler should encrypt credentials",
                    "check": "environment_variables_encrypted",
                    "severity": "high"
                },
                {
                    "issue": "Notification handler should have retry logic",
                    "check": "retry_logic_configured",
                    "severity": "medium"
                },
                {
                    "issue": "Notification handler should log delivery status",
                    "check": "logging_enabled",
                    "severity": "high"
                }
            ],
            LambdaIntent.DATA_TRANSFORMATION: [
                {
                    "issue": "Data transformation should have sufficient memory",
                    "check": "memory_appropriate_for_data",
                    "severity": "high"
                },
                {
                    "issue": "Data transformation should handle errors gracefully",
                    "check": "error_handling",
                    "severity": "high"
                },
                {
                    "issue": "Data transformation should be properly monitored",
                    "check": "logging_and_monitoring",
                    "severity": "medium"
                }
            ]
        }
        
        return intent_findings_map.get(intent, [])
