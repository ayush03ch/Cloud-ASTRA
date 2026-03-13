# agents/apigateway_agent/rules/default_endpoint_rule.py


class DefaultEndpointRule:
    """Check whether the default execute-api endpoint is disabled.

    Best practice: disable the default execute-api endpoint so that traffic
    can only reach the API through a custom domain (which can enforce stricter
    TLS/WAF settings).
    """

    id        = "apigw_default_endpoint_enabled"
    detection = "Default execute-api endpoint is enabled — custom domain not enforced"
    auto_safe = True

    def __init__(self):
        self.fix_instructions = [
            "Configure a custom domain name for the API",
            "In API Gateway → REST API → Settings → uncheck 'Enable default endpoint'",
            "Redeploy the API after disabling the default endpoint",
            "Ensure clients are using the custom domain before disabling",
            "CLI: aws apigateway update-rest-api --rest-api-id <id> --patch-operations op=replace,path=/disableExecuteApiEndpoint,value=true",
        ]
        self.can_auto_fix = True
        self.fix_type     = "disable_apigw_default_endpoint"

    def check(self, client, api_id: str, stage_name: str) -> bool:
        try:
            api = client.get_rest_api(restApiId=api_id)
            # disableExecuteApiEndpoint=True means it IS disabled (good); False means it IS enabled (bad)
            return not api.get("disableExecuteApiEndpoint", False)
        except Exception as e:
            print(f"Error checking default endpoint for {api_id}: {e}")
            return False
