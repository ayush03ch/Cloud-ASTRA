# agents/apigateway_agent/rules/access_logging_rule.py


class AccessLoggingRule:
    """Check that access logging is enabled on every deployed stage."""

    id        = "apigw_access_logging_disabled"
    detection = "Access logging is not enabled for API Gateway stage"
    auto_safe = False

    def __init__(self):
        self.fix_instructions = [
            "Open the API Gateway console and navigate to the stage",
            "Select the stage → Logs/Tracing tab",
            "Enable 'Access Logging' and set a CloudWatch Log Group ARN",
            "Use a log format such as: $context.requestId $context.status $context.identity.sourceIp",
            "Save and redeploy the stage",
        ]
        self.can_auto_fix = False
        self.fix_type     = None

    def check(self, client, api_id: str, stage_name: str) -> bool:
        try:
            stage = client.get_stage(restApiId=api_id, stageName=stage_name)
            access_log_settings = stage.get("accessLogSettings", {})
            return not access_log_settings.get("destinationArn")
        except Exception as e:
            print(f"Error checking access logging for {api_id}/{stage_name}: {e}")
            return False
