# agents/vpc_agent/rules/flow_logs_rule.py

class FlowLogsRule:
    id = "vpc_flow_logs_disabled"
    detection = "VPC does not have flow logs enabled"
    severity = "medium"
    auto_safe = False
    can_auto_fix = False
    fix_type = "enable_flow_logs"

    def __init__(self):
        self.fix_instructions = [
            "1. Open the VPC console and select your VPC",
            "2. Go to 'Flow Logs' tab and click 'Create flow log'",
            "3. Choose destination: CloudWatch Logs or S3",
            "4. Select or create an IAM role with permissions to publish logs",
            "5. Set the filter to 'All' to capture accept, reject, and all traffic",
        ]

    def check(self, client, vpc_id, vpc_info):
        try:
            response = client.describe_flow_logs(
                Filters=[{'Name': 'resource-id', 'Values': [vpc_id]}]
            )
            return len(response.get('FlowLogs', [])) == 0
        except Exception as e:
            print(f"[FlowLogsRule] Error checking {vpc_id}: {e}")
            return False

    def fix(self, client, vpc_id, vpc_info):
        print(f"⚠️ Manual fix required: enable VPC flow logs on {vpc_id}")
        return False
