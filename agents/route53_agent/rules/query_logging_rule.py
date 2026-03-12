# agents/route53_agent/rules/query_logging_rule.py

class QueryLoggingRule:
    """Check if query logging is enabled for security monitoring."""
    
    id = "route53_query_logging_disabled"
    detection = "Query logging not enabled for hosted zone"
    auto_safe = False  # Logging incurs costs
    
    def __init__(self):
        self.fix_instructions = [
            "⚠️ Query Logging Status: Disabled",
            "",
            "🔧 Steps to Enable Query Logging:",
            "1. Create a CloudWatch Logs log group in us-east-1",
            "2. Configure appropriate retention period (e.g., 30 days)",
            "3. In Route53 console, select the hosted zone",
            "4. Choose 'Query logging configuration'",
            "5. Click 'Configure query logging'",
            "6. Select the CloudWatch log group",
            "7. Logs will contain: query timestamp, domain, query type, response code",
            "",
            "💰 Note: CloudWatch Logs charges apply based on data ingested"
        ]
        self.can_auto_fix = False  # Requires CloudWatch log group setup
        self.fix_type = "enable_query_logging"
    
    def check(self, client, zone_id, zone_name):
        """Check if query logging is enabled."""
        try:
            response = client.list_query_logging_configs(HostedZoneId=zone_id)
            configs = response.get('QueryLoggingConfigs', [])
            
            # Issue if no query logging configs exist
            return len(configs) == 0
            
        except Exception as e:
            print(f"Error checking query logging for {zone_name}: {e}")
            return False
    
    def fix(self, client, zone_id, zone_name):
        """Enable query logging (requires CloudWatch log group)."""
        print(f"⚠️ Query logging requires CloudWatch log group setup")
        print(f"Follow the fix_instructions for {zone_name}")
        return False  # Manual setup required
