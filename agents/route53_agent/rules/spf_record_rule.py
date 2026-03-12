# agents/route53_agent/rules/spf_record_rule.py

class SPFRecordRule:
    """Check if SPF records are properly configured for email domains."""
    
    id = "route53_missing_spf_record"
    detection = "SPF record missing or improperly configured"
    auto_safe = False  # SPF records require careful configuration
    
    def __init__(self):
        self.fix_instructions = [
            "⚠️ SPF Record Status: Missing or Misconfigured",
            "",
            "🔧 Steps to Add/Fix SPF Record:",
            "1. Identify all mail servers that send email for your domain",
            "2. In Route53 console, select the hosted zone",
            "3. Create or update TXT record at apex domain",
            "4. Record name: @ or leave blank",
            "5. Record type: TXT",
            "6. Value format: \"v=spf1 [mechanisms] [qualifier]\"",
            "",
            "📧 Common SPF Examples:",
            "- Google Workspace: \"v=spf1 include:_spf.google.com ~all\"",
            "- Microsoft 365: \"v=spf1 include:spf.protection.outlook.com ~all\"",
            "- SendGrid: \"v=spf1 include:sendgrid.net ~all\"",
            "- Multiple sources: \"v=spf1 include:_spf.google.com include:sendgrid.net ~all\"",
            "",
            "🔍 SPF Qualifiers:",
            "- ~all (SoftFail): Recommended for most cases",
            "- -all (Fail): Strict rejection, use carefully",
            "- ?all (Neutral): Not recommended",
            "",
            "⚠️ Test SPF record before enabling strict policy"
        ]
        self.can_auto_fix = False  # Requires knowing authorized mail servers
        self.fix_type = "configure_spf_record"
    
    def check(self, client, zone_id, zone_name):
        """Check if SPF record exists and is valid."""
        try:
            # First check if domain has MX records (email domain)
            response = client.list_resource_record_sets(HostedZoneId=zone_id)
            record_sets = response.get('ResourceRecordSets', [])
            
            mx_records = [r for r in record_sets if r.get('Type') == 'MX']
            
            # Only check SPF if domain has MX records
            if not mx_records:
                return False  # Not an email domain
            
            # Look for SPF records (TXT records with v=spf1)
            apex_txt_records = [
                r for r in record_sets 
                if r.get('Type') == 'TXT' 
                and r.get('Name', '').rstrip('.') == zone_name.rstrip('.')
            ]
            
            spf_records = []
            for record in apex_txt_records:
                for resource_record in record.get('ResourceRecords', []):
                    value = resource_record.get('Value', '').strip('"')
                    if value.startswith('v=spf1'):
                        spf_records.append(value)
            
            # Issue if no SPF record or improperly configured
            if not spf_records:
                return True
            
            # Check for common SPF issues
            for spf in spf_records:
                # Check if it ends with a qualifier
                if not any(spf.endswith(q) for q in ['~all', '-all', '?all', '+all']):
                    return True  # Missing all mechanism
            
            return False
            
        except Exception as e:
            print(f"Error checking SPF record for {zone_name}: {e}")
            return False
    
    def fix(self, client, zone_id, zone_name):
        """Configure SPF record (requires mail server information)."""
        print(f"⚠️ SPF record configuration requires mail server details")
        print(f"Follow the fix_instructions for {zone_name}")
        return False  # Manual configuration required
