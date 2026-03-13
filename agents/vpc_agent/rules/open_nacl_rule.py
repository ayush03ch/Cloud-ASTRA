# agents/vpc_agent/rules/open_nacl_rule.py

class OpenNACLRule:
    id = "vpc_open_nacl"
    detection = "A Network ACL in this VPC allows all inbound traffic on all ports"
    severity = "high"
    auto_safe = False
    can_auto_fix = False
    fix_type = "restrict_nacl"

    def __init__(self):
        self.fix_instructions = [
            "1. Open the VPC console and navigate to 'Network ACLs'",
            "2. Review each NACL's inbound rules",
            "3. Remove or restrict rules with port range 0-65535 and CIDR 0.0.0.0/0",
            "4. Replace broad rules with specific rules allowing only necessary traffic",
            "⚠️ NACL changes apply immediately and can disrupt active connections",
        ]

    def check(self, client, vpc_id, vpc_info):
        try:
            response = client.describe_network_acls(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            for nacl in response.get('NetworkAcls', []):
                for entry in nacl.get('Entries', []):
                    if (
                        entry.get('Egress') is False
                        and entry.get('RuleAction') == 'allow'
                        and entry.get('Protocol') == '-1'
                        and (
                            entry.get('CidrBlock') == '0.0.0.0/0'
                            or entry.get('Ipv6CidrBlock') == '::/0'
                        )
                    ):
                        return True
            return False
        except Exception as e:
            print(f"[OpenNACLRule] Error checking {vpc_id}: {e}")
            return False

    def fix(self, client, vpc_id, vpc_info):
        print(f"⚠️ Manual fix required: restrict NACL rules in VPC {vpc_id}")
        return False
