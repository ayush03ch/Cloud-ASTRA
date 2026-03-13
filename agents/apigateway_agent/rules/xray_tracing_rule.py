# agents/apigateway_agent/rules/xray_tracing_rule.py


class XRayTracingRule:
    """Check that AWS X-Ray active tracing is enabled on the stage."""

    id        = "apigw_xray_tracing_disabled"
    detection = "X-Ray active tracing is not enabled for API Gateway stage"
    auto_safe = True

    def __init__(self):
        self.fix_instructions = [
            "Go to API Gateway → Stages → select your stage",
            "Under 'Logs/Tracing', enable 'X-Ray Tracing'",
            "Redeploy the stage",
            "CLI: aws apigateway update-stage --rest-api-id <id> --stage-name <name> "
            "--patch-operations op=replace,path=/tracingEnabled,value=true",
        ]
        self.can_auto_fix = True
        self.fix_type     = "enable_apigw_xray_tracing"

    def check(self, client, api_id: str, stage_name: str) -> bool:
        try:
            stage = client.get_stage(restApiId=api_id, stageName=stage_name)
            return not stage.get("tracingEnabled", False)
        except Exception as e:
            print(f"Error checking X-Ray tracing for {api_id}/{stage_name}: {e}")
            return False
