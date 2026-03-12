# agents/route53_agent/rules/dmarc_record_rule.py

class DMARCRecordRule:
    """Check if DMARC record is configured for email authentication."""
    
    id = "route53_missing_dmarc_record"
    detection = "DMARC record missing for email domain"
    auto_safe = False  # DMARC can affect email delivery
    
    def __init__(self):
        self.fix_instructions = [
            "⚠️ DMARC Record Status: Not Configured",
            "",
            "🔧 Steps to Add DMARC Record:",
            "1. Decide on DMARC policy (start with p=none for monitoring)",
            "2. Set up email address to receive DMARC reports",
            "3. In Route53 console, select the hosted zone",
            "4. Create TXT record at _dmarc subdomain",
            "5. Record name: _dmarc",
            "6. Record type: TXT",
            "7. Value format: \"v=DMARC1; p=[policy]; rua=mailto:[email]\"",
            "",
            "📧 DMARC Policy Examples:",
            "- Monitoring only: \"v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com\"",
            "- Quarantine: \"v=DMARC1; p=quarantine; pct=10; rua=mailto:dmarc@yourdomain.com\"",
            "- Reject: \"v=DMARC1; p=reject; rua=mailto:dmarc@yourdomain.com\"",
            "",
            "🔍 DMARC Policy Levels:",
            "- p=none: Monitor only (recommended to start)",
            "- p=quarantine: Mark suspicious emails as spam",
            "- p=reject: Reject unauthenticated emails",
            "",
            "📊 DMARC Reports:",
            "- rua: Aggregate reports (daily)",
            "- ruf: Forensic reports (per-message)",
            "",
            "⚠️ Start with p=none and monitor reports before enforcing"
        ]
        self.can_auto_fix = False  # Requires email configuration
        self.fix_type = "configure_dmarc_record"
    
    def check(self, client, zone_id, zone_name):
        """Check if DMARC record exists."""
        try:
            # First check if domain has MX records (email domain)
            response = client.list_resource_record_sets(HostedZoneId=zone_id)
            record_sets = response.get('ResourceRecordSets', [])
            
            mx_records = [r for r in record_sets if r.get('Type') == 'MX']
            
            # Only check DMARC if domain has MX records
            if not mx_records:
                return False  # Not an email domain
            
            # Look for DMARC record at _dmarc subdomain
            dmarc_name = f"_dmarc.{zone_name}".rstrip('.')
            dmarc_records = [
                r for r in record_sets 
                if r.get('Type') == 'TXT' 
                and r.get('Name', '').rstrip('.') == dmarc_name
            ]
            
            if not dmarc_records:
                return True  # DMARC record missing
            
            # Validate DMARC record format
            for record in dmarc_records:
                for resource_record in record.get('ResourceRecords', []):
                    value = resource_record.get('Value', '').strip('"')
                    if value.startswith('v=DMARC1'):
                        return False  # Valid DMARC record found
            
            return True  # DMARC record exists but invalid
            
        except Exception as e:
            print(f"Error checking DMARC record for {zone_name}: {e}")
            return False
    
    def fix(self, client, zone_id, zone_name):
        """Configure DMARC record (requires policy decision)."""
        print(f"⚠️ DMARC record configuration requires policy and email setup")
        print(f"Follow the fix_instructions for {zone_name}")
        return False  # Manual configuration required
