# agents/vpc_agent/rules/default_sg_rule.py

class DefaultSGRule:
    id = "vpc_default_security_group_open"
    detection = "The default security group of the VPC has inbound or outbound rules"
    severity = "high"
    auto_safe = False
    can_auto_fix = False
    fix_type = "restrict_default_sg"

    def __init__(self):
        self.fix_instructions = [
            "1. Open the EC2 console and navigate to 'Security Groups'",
            "2. Find the 'default' security group for this VPC",
            "3. Remove all inbound rules from the default security group",
            "4. Remove all outbound rules from the default security group",
            "5. Ensure no instances use the default SG — create dedicated groups instead",
        ]

    def check(self, client, vpc_id, vpc_info):
        try:
            response = client.describe_security_groups(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'group-name', 'Values': ['default']},
                ]
            )
            for sg in response.get('SecurityGroups', []):
                if sg.get('IpPermissions') or sg.get('IpPermissionsEgress'):
                    return True
            return False
        except Exception as e:
            print(f"[DefaultSGRule] Error checking {vpc_id}: {e}")
            return False

    def fix(self, client, vpc_id, vpc_info):
        print(f"⚠️ Manual fix required: remove rules from default security group in {vpc_id}")
        return False
