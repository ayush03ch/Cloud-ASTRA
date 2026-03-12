# agents/route53_agent/executor.py

import boto3
from typing import Dict, List


class Route53Executor:
    """
    Executes Route53 operations and formats findings for FixerAgent.
    """

    def __init__(self):
        pass

    def format_for_fixer(self, findings: List[Dict]) -> List[Dict]:
        """
        Format findings into standardized structure for FixerAgent.
        
        Args:
            findings: List of finding dicts from Route53Agent
            
        Returns:
            List of formatted findings
        """
        formatted = []
        
        for finding in findings:
            formatted_finding = {
                "service": "route53",
                "resource": finding.get("resource", "unknown-zone"),
                "zone_id": finding.get("zone_id", ""),
                "issue": finding.get("issue", "Unknown issue"),
                "severity": finding.get("severity", "medium"),
                "rule_id": finding.get("rule_id", "unknown"),
                "auto_safe": finding.get("auto_safe", False),
                "fix_instructions": finding.get("fix_instructions", []),
                "can_auto_fix": finding.get("can_auto_fix", False),
                "fix_type": finding.get("fix_type"),
                "details": finding.get("details", finding.get("description", "")),
                "source": finding.get("source", "unknown"),
                "tier": finding.get("tier", 0),
                "intent": finding.get("intent", "unknown"),
                "intent_confidence": finding.get("intent_confidence", 0.0)
            }
            
            # Add execution metadata if available
            if "action" in finding:
                formatted_finding["action"] = finding["action"]
            if "params" in finding:
                formatted_finding["params"] = finding["params"]
            
            formatted.append(formatted_finding)
        
        return formatted

    def enable_dnssec(self, client, zone_id: str) -> bool:
        """Enable DNSSEC for a hosted zone."""
        try:
            client.enable_hosted_zone_dnssec(HostedZoneId=zone_id)
            print(f"✅ Enabled DNSSEC for zone {zone_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to enable DNSSEC for zone {zone_id}: {e}")
            return False

    def enable_query_logging(self, client, zone_id: str, log_group_arn: str) -> bool:
        """Enable query logging for a hosted zone."""
        try:
            client.create_query_logging_config(
                HostedZoneId=zone_id,
                CloudWatchLogsLogGroupArn=log_group_arn
            )
            print(f"✅ Enabled query logging for zone {zone_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to enable query logging for zone {zone_id}: {e}")
            return False

    def create_health_check(self, client, config: Dict) -> bool:
        """Create a health check for monitoring."""
        try:
            response = client.create_health_check(
                CallerReference=config.get('caller_reference'),
                HealthCheckConfig=config.get('health_check_config')
            )
            print(f"✅ Created health check {response['HealthCheck']['Id']}")
            return True
        except Exception as e:
            print(f"❌ Failed to create health check: {e}")
            return False

    def update_record_set(self, client, zone_id: str, changes: List[Dict]) -> bool:
        """Update DNS record sets in a hosted zone."""
        try:
            client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    'Changes': changes
                }
            )
            print(f"✅ Updated record sets for zone {zone_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to update record sets for zone {zone_id}: {e}")
            return False
