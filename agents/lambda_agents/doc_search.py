# agents/lambda_agents/doc_search.py

class DocSearch:
    def __init__(self):
        # Intent-specific documentation references
        self.intent_docs = {
            "api_endpoint": {
                "common_issues": [
                    "Function logs not accessible",
                    "Environment variables exposed in logs",
                    "Timeout too short for API requests",
                    "Memory allocation insufficient"
                ],
                "aws_docs": "https://docs.aws.amazon.com/lambda/latest/dg/API_CreateFunction.html",
                "best_practices": [
                    "Enable CloudWatch Logs for debugging",
                    "Use KMS encryption for environment variables",
                    "Set appropriate timeout (30s-300s for APIs)",
                    "Allocate sufficient memory (256MB minimum)"
                ]
            },
            "scheduled_task": {
                "common_issues": [
                    "Execution failures not monitored",
                    "Sensitive data in environment variables",
                    "Timeout too short for batch operations",
                    "No dead-letter queue for failed invocations"
                ],
                "aws_docs": "https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchevents.html",
                "best_practices": [
                    "Enable CloudWatch Logs for audit trail",
                    "Encrypt environment variables with KMS",
                    "Set timeout appropriate for task duration",
                    "Configure dead-letter queue for error handling"
                ]
            },
            "event_processor": {
                "common_issues": [
                    "Processing errors not logged",
                    "Credentials exposed in function code",
                    "Batch size not optimized",
                    "Error handling missing"
                ],
                "aws_docs": "https://docs.aws.amazon.com/lambda/latest/dg/invocation-eventsourcemapping.html",
                "best_practices": [
                    "Log all events and errors to CloudWatch",
                    "Store credentials in environment variables",
                    "Optimize batch size for throughput",
                    "Implement proper error handling and retries"
                ]
            },
            "stream_processor": {
                "common_issues": [
                    "Stream records not being processed",
                    "Batch window not optimized",
                    "Parallelization issues",
                    "Failed records not tracked"
                ],
                "aws_docs": "https://docs.aws.amazon.com/lambda/latest/dg/with-kinesis.html",
                "best_practices": [
                    "Enable function response types for proper error reporting",
                    "Set batch size and window for optimal throughput",
                    "Implement parallel record processing",
                    "Configure DLQ for failed batches"
                ]
            },
            "notification_handler": {
                "common_issues": [
                    "Notification delivery not tracked",
                    "API keys stored insecurely",
                    "Timeout insufficient for external API calls",
                    "No retry mechanism"
                ],
                "aws_docs": "https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html",
                "best_practices": [
                    "Log notification delivery status",
                    "Use KMS to encrypt sensitive credentials",
                    "Set timeout for external API interactions",
                    "Implement exponential backoff for retries"
                ]
            },
            "data_transformation": {
                "common_issues": [
                    "Memory exceeded for large datasets",
                    "Transformation logic not logged",
                    "No checkpointing for partial failures",
                    "Performance bottlenecks not identified"
                ],
                "aws_docs": "https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html",
                "best_practices": [
                    "Allocate sufficient memory for data processing",
                    "Log transformation steps for debugging",
                    "Implement checkpoint logic for resumability",
                    "Monitor memory and duration metrics"
                ]
            }
        }
    
    def search(self, issue, intent=None):
        """
        Enhanced doc search with intent context.
        
        Args:
            issue: The detected issue
            intent: User's detected intent (e.g., "api_endpoint", "scheduled_task")
        """
        if intent and intent in self.intent_docs:
            docs = self.intent_docs[intent]
            
            # Find most relevant issue
            relevant_issue = None
            for common_issue in docs["common_issues"]:
                if any(keyword in issue.lower() for keyword in common_issue.lower().split()):
                    relevant_issue = common_issue
                    break
            
            if relevant_issue:
                return {
                    "issue_type": relevant_issue,
                    "intent": intent,
                    "aws_docs": docs["aws_docs"],
                    "best_practices": docs["best_practices"],
                    "suggestion": f"For {intent}, {relevant_issue} is a common issue. Review best practices."
                }
        
        # Fallback to generic search
        return f"No direct rule found. Refer to AWS Lambda Docs for: {issue}"
