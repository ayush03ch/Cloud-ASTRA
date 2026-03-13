# agents/route53_agent/rules/wildcard_record_rule.py

class WildcardRecordRule:
    """Check for potentially dangerous wildcard DNS records."""
    
    id = "route53_wildcard_records"
    detection = "Wildcard DNS records detected - potential security risk"
    auto_safe = True  # Safe to auto-delete wildcard records
    
    def __init__(self):
        self.fix_instructions = [
            "⚠️ Wildcard Record Detected: *.domain.com",
            "",
            "🔍 Security Concerns:",
            "- Wildcard records match ANY subdomain",
            "- Can expose internal services unintentionally",
            "- May allow subdomain takeover attacks",
            "- Difficult to control certificate issuance scope",
            "",
            "🔧 Recommended Actions:",
            "1. Review all wildcard records (*.domain.com)",
            "2. Replace with explicit subdomain records where possible",
            "3. If wildcard is necessary:",
            "   a. Ensure backend properly validates Host headers",
            "   b. Use wildcard certificates carefully",
            "   c. Monitor for unexpected subdomain requests",
            "4. Consider using specific records instead:",
            "   - api.domain.com",
            "   - app.domain.com",
            "   - www.domain.com",
            "",
            "💡 Explicit records are more secure than wildcards"
        ]
        self.can_auto_fix = True  # Can automatically delete wildcard records
        self.fix_type = "delete_wildcard_records"
    
    def check(self, client, zone_id, zone_name):
        """Check for wildcard DNS records."""
        try:
            # Get all records in the zone
            response = client.list_resource_record_sets(HostedZoneId=zone_id)
            record_sets = response.get('ResourceRecordSets', [])
            
            # Look for wildcard records
            wildcard_records = [
                r for r in record_sets 
                if r.get('Name', '').startswith('\\052.')  # \052 is octal for *
                or r.get('Name', '').startswith('*.')
            ]
            
            return len(wildcard_records) > 0
            
        except Exception as e:
            print(f"Error checking wildcard records for {zone_name}: {e}")
            return False
    
    def fix(self, client, zone_id, zone_name):
        """Delete all wildcard DNS records from the hosted zone."""
        try:
            response = client.list_resource_record_sets(HostedZoneId=zone_id)
            record_sets = response.get('ResourceRecordSets', [])

            wildcard_records = [
                r for r in record_sets
                if r.get('Name', '').startswith('\\052.')
                or r.get('Name', '').startswith('*.')
            ]

            if not wildcard_records:
                print(f"No wildcard records found in {zone_name}")
                return True

            changes = [
                {"Action": "DELETE", "ResourceRecordSet": record}
                for record in wildcard_records
            ]

            client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={"Changes": changes}
            )
            print(f"✅ Deleted {len(wildcard_records)} wildcard record(s) from {zone_name}")
            return True

        except Exception as e:
            print(f"❌ Failed to delete wildcard records from {zone_name}: {e}")
            return False
