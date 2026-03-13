# agents/apigateway_agent/rules/waf_rule.py


class WAFAssociationRule:
    """Check that a WAF Web ACL is associated with the API Gateway stage."""

    id        = "apigw_waf_not_associated"
    detection = "No WAF Web ACL is associated with the API Gateway stage"
    auto_safe = False   # Associating a WAF requires knowing the WebACL ARN — needs manual input

    def __init__(self):
        self.fix_instructions = [
            "Create a WAF Web ACL in AWS WAFv2 with appropriate rules (AWSManagedRulesCommonRuleSet, etc.)",
            "In API Gateway console → Stage → select stage → Settings",
            "Under 'Web Application Firewall', choose your WAF Web ACL",
            "Save Changes and redeploy the stage",
            "CLI: aws wafv2 associate-web-acl --web-acl-arn <ARN> --resource-arn <stage-arn>",
        ]
        self.can_auto_fix = False
        self.fix_type     = None

    def check(self, client, api_id: str, stage_name: str) -> bool:
        try:
            stage = client.get_stage(restApiId=api_id, stageName=stage_name)
            return not stage.get("webAclArn")
        except Exception as e:
            print(f"Error checking WAF for {api_id}/{stage_name}: {e}")
            return False
