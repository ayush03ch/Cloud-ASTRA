# agents/route53_agent/rules/dnssec_rule.py

class DNSSECRule:
    """Check if DNSSEC is enabled for public hosted zones."""
    
    id = "route53_dnssec_disabled"
    detection = "DNSSEC not enabled for public hosted zone"
    auto_safe = False  # DNSSEC requires careful setup
    
    def __init__(self):
        self.fix_instructions = [
            "⚠️ DNSSEC Status: Disabled",
            "",
            "🔧 Steps to Enable DNSSEC:",
            "1. Ensure your domain registrar supports DNSSEC",
            "2. In Route53 console, select the hosted zone",
            "3. Choose 'DNSSEC signing' tab",
            "4. Click 'Enable DNSSEC signing'",
            "5. Route53 will create a KSK (Key Signing Key)",
            "6. Add the DS record to your domain registrar",
            "7. Wait for DNS propagation (can take 24-48 hours)",
            "",
            "⚠️ Important: Test thoroughly before enabling in production"
        ]
        self.can_auto_fix = False  # Requires registrar configuration
        self.fix_type = "enable_dnssec"
    
    def check(self, client, zone_id, zone_name):
        """Check if DNSSEC is enabled."""
        try:
            # Check if zone is private (DNSSEC only for public zones)
            zone_response = client.get_hosted_zone(Id=zone_id)
            is_private = zone_response.get('HostedZone', {}).get('Config', {}).get('PrivateZone', False)
            
            if is_private:
                return False  # DNSSEC not applicable to private zones
            
            # Check DNSSEC status
            dnssec_response = client.get_dnssec(HostedZoneId=zone_id)
            status = dnssec_response.get('Status', {}).get('ServeSignature')
            
            # Issue if DNSSEC is not serving signatures
            return status != 'SIGNING'
            
        except client.exceptions.DNSSECNotFound:
            # DNSSEC not configured at all
            return True
        except Exception as e:
            print(f"Error checking DNSSEC for {zone_name}: {e}")
            return False
    
    def fix(self, client, zone_id, zone_name):
        """Enable DNSSEC (requires manual registrar configuration)."""
        print(f"⚠️ DNSSEC enablement requires manual steps at domain registrar")
        print(f"Follow the fix_instructions for {zone_name}")
        return False  # Manual intervention required
