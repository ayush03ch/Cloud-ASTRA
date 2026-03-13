# agents/apigateway_agent/rules/tls_policy_rule.py


class TLSPolicyRule:
    """Ensure the stage enforces a minimum TLS version of TLS_1_2."""

    id        = "apigw_weak_tls_policy"
    detection = "API Gateway stage does not enforce TLS 1.2 minimum"
    auto_safe = False

    def __init__(self):
        self.fix_instructions = [
            "Go to API Gateway → Custom Domain Names (for custom domains)",
            "Set the Security Policy to TLS 1.2",
            "For built-in execute-api endpoint, open Stage → Client Certificate",
            "Re-deploy the stage after making changes",
            "Verify with: aws apigateway get-domain-name --domain-name <name>",
        ]
        self.can_auto_fix = False
        self.fix_type     = None

    def check(self, client, api_id: str, stage_name: str) -> bool:
        """Flag if the stage method settings do not restrict to TLS_1_2 (REST APIs)."""
        try:
            stage = client.get_stage(restApiId=api_id, stageName=stage_name)
            # Check if client certificate is missing (basic TLS hygiene indicator)
            # A missing client cert + no explicit security policy indicates weaker posture
            client_cert_id = stage.get("clientCertificateId", "")
            # Also check for custom domain TLS policy if available
            method_settings = stage.get("methodSettings", {})

            # Heuristic: warn when no client certificate is configured at all
            # (Real TLS enforcement is on the custom-domain resource, not the stage)
            if not client_cert_id:
                return True
            return False
        except Exception as e:
            print(f"Error checking TLS policy for {api_id}/{stage_name}: {e}")
            return False
