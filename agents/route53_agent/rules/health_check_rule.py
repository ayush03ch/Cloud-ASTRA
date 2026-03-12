# agents/route53_agent/rules/health_check_rule.py

class HealthCheckRule:
    """Check if critical records have health checks configured."""
    
    id = "route53_missing_health_checks"
    detection = "Critical DNS records missing health checks"
    auto_safe = False  # Health checks require endpoint configuration
    
    def __init__(self):
        self.fix_instructions = [
            "⚠️ Health Check Status: Not Configured",
            "",
            "🔧 Steps to Create Health Checks:",
            "1. In Route53 console, go to 'Health checks'",
            "2. Click 'Create health check'",
            "3. Choose protocol (HTTP, HTTPS, TCP)",
            "4. Enter endpoint IP or domain name",
            "5. Configure check interval (30s or 10s for fast failover)",
            "6. Set failure threshold (typically 3 consecutive failures)",
            "7. Optional: Enable CloudWatch alarms for notifications",
            "8. Associate health check with DNS record",
            "",
            "💡 Best Practice: Create health checks for all critical endpoints"
        ]
        self.can_auto_fix = False  # Requires endpoint and configuration details
        self.fix_type = "create_health_checks"
    
    def check(self, client, zone_id, zone_name):
        """Check if critical records have health checks."""
        try:
            # Get all records in the zone
            response = client.list_resource_record_sets(HostedZoneId=zone_id)
            record_sets = response.get('ResourceRecordSets', [])
            
            # Look for A or AAAA records without health checks
            # Exclude NS and SOA records
            critical_records = [
                r for r in record_sets 
                if r.get('Type') in ['A', 'AAAA', 'CNAME'] 
                and not r.get('Name', '').startswith('_')  # Exclude service records
                and r.get('SetIdentifier')  # Only check weighted/failover records
            ]
            
            # Check if any critical records lack health checks
            records_without_health_checks = [
                r for r in critical_records
                if not r.get('HealthCheckId')
            ]
            
            return len(records_without_health_checks) > 0
            
        except Exception as e:
            print(f"Error checking health checks for {zone_name}: {e}")
            return False
    
    def fix(self, client, zone_id, zone_name):
        """Create health checks (requires manual configuration)."""
        print(f"⚠️ Health check creation requires endpoint details")
        print(f"Follow the fix_instructions for {zone_name}")
        return False  # Manual configuration required
