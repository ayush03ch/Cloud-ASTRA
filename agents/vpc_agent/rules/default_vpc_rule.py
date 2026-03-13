# agents/vpc_agent/rules/default_vpc_rule.py

class DefaultVPCRule:
    id = "vpc_default_in_use"
    detection = "The default VPC is present and may be in use"
    severity = "medium"
    auto_safe = False
    can_auto_fix = False
    fix_type = "remove_default_vpc"

    def __init__(self):
        self.fix_instructions = [
            "1. Ensure no production resources are using the default VPC",
            "2. Migrate any workloads to a custom, purpose-built VPC",
            "3. Once empty, delete the default VPC:",
            "   aws ec2 delete-vpc --vpc-id <default-vpc-id>",
            "⚠️ The default VPC can be recreated with: aws ec2 create-default-vpc",
        ]

    def check(self, client, vpc_id, vpc_info):
        return vpc_info.get('IsDefault', False)

    def fix(self, client, vpc_id, vpc_info):
        print(f"⚠️ Manual fix required: evaluate and potentially delete default VPC {vpc_id}")
        return False
