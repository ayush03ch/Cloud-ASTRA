# agents/route53_agent/rules/caa_record_rule.py

class CAARecordRule:
    """Check if CAA records are configured to control certificate issuance."""
    
    id = "route53_missing_caa_records"
    detection = "CAA records not configured for domain"
    auto_safe = False  # CAA records can block certificate issuance if misconfigured
    
    def __init__(self):
        self.fix_instructions = [
            "⚠️ CAA Records Status: Not Configured",
            "",
            "🔧 Steps to Add CAA Records:",
            "1. Determine which Certificate Authorities you want to allow",
            "   - For AWS Certificate Manager: amazon.com",
            "   - For Let's Encrypt: letsencrypt.org",
            "   - For DigiCert: digicert.com",
            "2. In Route53 console, select the hosted zone",
            "3. Click 'Create record'",
            "4. Record name: (leave blank for apex domain or enter subdomain)",
            "5. Record type: CAA",
            "6. Value format: [flags] [tag] [value]",
            "   Example: 0 issue \"letsencrypt.org\"",
            "   Example: 0 issuewild \"amazon.com\"",
            "7. Create separate records for each CA you want to allow",
            "",
            "💡 CAA records prevent unauthorized certificate issuance",
            "⚠️ Ensure you list all CAs you use, or certificate renewals may fail"
        ]
        self.can_auto_fix = False  # Requires knowing which CAs to allow
        self.fix_type = "add_caa_records"
    
    def check(self, client, zone_id, zone_name):
        """Check if CAA records exist."""
        try:
            # Get all records in the zone
            response = client.list_resource_record_sets(HostedZoneId=zone_id)
            record_sets = response.get('ResourceRecordSets', [])
            
            # Check for CAA records
            caa_records = [r for r in record_sets if r.get('Type') == 'CAA']
            
            # Issue if no CAA records exist for public zones
            zone_response = client.get_hosted_zone(Id=zone_id)
            is_private = zone_response.get('HostedZone', {}).get('Config', {}).get('PrivateZone', False)
            
            if is_private:
                return False  # CAA records not needed for private zones
            
            return len(caa_records) == 0
            
        except Exception as e:
            print(f"Error checking CAA records for {zone_name}: {e}")
            return False
    
    def fix(self, client, zone_id, zone_name):
        """Add CAA records (requires CA selection)."""
        print(f"⚠️ CAA record creation requires Certificate Authority selection")
        print(f"Follow the fix_instructions for {zone_name}")
        return False  # Manual configuration required
