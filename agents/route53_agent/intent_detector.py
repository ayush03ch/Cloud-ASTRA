# agents/route53_agent/intent_detector.py

from enum import Enum
from typing import Dict, Tuple
import re


class Route53Intent(Enum):
    """Possible intents for Route53 hosted zones"""
    PUBLIC_WEBSITE = "public_website"
    API_SERVICE = "api_service"
    EMAIL_DOMAIN = "email_domain"
    INTERNAL_SERVICE = "internal_service"
    CDN_DISTRIBUTION = "cdn_distribution"
    SUBDOMAIN_DELEGATION = "subdomain_delegation"
    LOAD_BALANCER = "load_balancer"
    MULTI_REGION = "multi_region"
    UNKNOWN = "unknown"


class Route53IntentDetector:
    """Detects the intent/purpose of a Route53 hosted zone."""

    def __init__(self):
        self.intent_keywords = {
            Route53Intent.PUBLIC_WEBSITE: ['www', 'web', 'site', 'blog', 'portal'],
            Route53Intent.API_SERVICE: ['api', 'service', 'gateway', 'endpoint'],
            Route53Intent.EMAIL_DOMAIN: ['mail', 'mx', 'smtp', 'email'],
            Route53Intent.INTERNAL_SERVICE: ['internal', 'private', 'corp', 'intranet'],
            Route53Intent.CDN_DISTRIBUTION: ['cdn', 'cloudfront', 'static', 'assets'],
            Route53Intent.SUBDOMAIN_DELEGATION: ['dev', 'staging', 'test', 'prod'],
            Route53Intent.LOAD_BALANCER: ['lb', 'elb', 'alb', 'nlb', 'balancer'],
            Route53Intent.MULTI_REGION: ['global', 'multi', 'geo', 'failover']
        }

    def detect_intent(
        self,
        zone_id: str,
        zone_name: str,
        client,
        user_intent: str = None
    ) -> Tuple[Route53Intent, float, str]:
        """
        Detect the intent of a hosted zone.
        
        Args:
            zone_id: Route53 hosted zone ID
            zone_name: Domain name of the hosted zone
            client: Boto3 Route53 client
            user_intent: Optional explicit user intent
            
        Returns:
            Tuple of (intent, confidence, reasoning)
        """
        # Priority 1: Explicit user intent
        if user_intent:
            intent = self._parse_user_intent(user_intent)
            if intent != Route53Intent.UNKNOWN:
                return intent, 1.0, f"User explicitly specified: {user_intent}"

        # Priority 2: Check if it's a private hosted zone
        try:
            zone_response = client.get_hosted_zone(Id=zone_id)
            if zone_response.get('HostedZone', {}).get('Config', {}).get('PrivateZone', False):
                return Route53Intent.INTERNAL_SERVICE, 0.9, "Private hosted zone detected"
        except:
            pass

        # Priority 3: Analyze DNS records
        try:
            records = client.list_resource_record_sets(HostedZoneId=zone_id)
            record_sets = records.get('ResourceRecordSets', [])
            
            # Check for specific record patterns
            has_mx_records = any(r.get('Type') == 'MX' for r in record_sets)
            has_txt_spf = any(r.get('Type') == 'TXT' and 'spf' in str(r.get('ResourceRecords', [])).lower() for r in record_sets)
            has_a_records = any(r.get('Type') == 'A' for r in record_sets)
            has_cname_cdn = any(r.get('Type') == 'CNAME' and ('cloudfront' in str(r.get('ResourceRecords', [])).lower() or 'cdn' in str(r.get('ResourceRecords', [])).lower()) for r in record_sets)
            has_alias_records = any(r.get('AliasTarget') is not None for r in record_sets)
            has_weighted_routing = any(r.get('Weight') is not None for r in record_sets)
            has_geolocation = any(r.get('GeoLocation') is not None for r in record_sets)
            
            # Intent detection logic
            if has_mx_records and has_txt_spf:
                return Route53Intent.EMAIL_DOMAIN, 0.85, "MX and SPF records detected"
            
            if has_cname_cdn:
                return Route53Intent.CDN_DISTRIBUTION, 0.8, "CloudFront/CDN CNAME records detected"
            
            if has_weighted_routing or has_geolocation:
                return Route53Intent.MULTI_REGION, 0.8, "Traffic routing policies detected (weighted/geo)"
            
            if has_alias_records:
                # Check if pointing to load balancers
                lb_aliases = [r for r in record_sets if r.get('AliasTarget') and 
                            ('elb' in str(r.get('AliasTarget', {}).get('DNSName', '')).lower() or
                             'alb' in str(r.get('AliasTarget', {}).get('DNSName', '')).lower())]
                if lb_aliases:
                    return Route53Intent.LOAD_BALANCER, 0.85, "Alias records pointing to load balancers"
            
            # Check zone name for hints
            zone_lower = zone_name.lower()
            for intent, keywords in self.intent_keywords.items():
                for keyword in keywords:
                    if keyword in zone_lower:
                        return intent, 0.7, f"Zone name contains '{keyword}'"
            
            # Default for public zones with A records
            if has_a_records:
                return Route53Intent.PUBLIC_WEBSITE, 0.6, "Public zone with A records (likely website)"
            
        except Exception as e:
            print(f"Error analyzing records for zone {zone_name}: {e}")
        
        return Route53Intent.UNKNOWN, 0.3, "Unable to determine intent from available data"

    def _parse_user_intent(self, user_intent: str) -> Route53Intent:
        """Parse user-provided intent string into Route53Intent enum."""
        user_intent_lower = user_intent.lower().replace(" ", "_").replace("-", "_")
        
        for intent in Route53Intent:
            if intent.value == user_intent_lower or user_intent_lower in intent.value:
                return intent
        
        return Route53Intent.UNKNOWN

    def get_intent_recommendations(self, intent: Route53Intent, zone_name: str) -> Dict:
        """Get security recommendations based on detected intent."""
        recommendations = {
            Route53Intent.PUBLIC_WEBSITE: {
                "dnssec": "Enable DNSSEC for domain integrity",
                "caa_records": "Add CAA records to control certificate issuance",
                "health_checks": "Configure health checks for high availability",
                "query_logging": "Enable query logging for security monitoring",
                "subdomain_wildcards": "Review wildcard records for security risks"
            },
            Route53Intent.API_SERVICE: {
                "dnssec": "Enable DNSSEC for API endpoint integrity",
                "health_checks": "Mandatory health checks for API availability",
                "failover": "Consider failover routing for redundancy",
                "query_logging": "Enable query logging for API monitoring",
                "ssl_tls": "Ensure TLS/SSL certificate records are valid"
            },
            Route53Intent.EMAIL_DOMAIN: {
                "spf_records": "Verify SPF records are configured correctly",
                "dkim_records": "Add DKIM records for email authentication",
                "dmarc_records": "Implement DMARC policy for email security",
                "mx_records": "Ensure MX records have backup servers",
                "dnssec": "Enable DNSSEC to prevent DNS spoofing"
            },
            Route53Intent.INTERNAL_SERVICE: {
                "private_zone": "Verify zone is truly private",
                "vpc_association": "Review VPC associations",
                "query_logging": "Enable query logging for internal monitoring",
                "access_control": "Restrict Route53 API access with IAM policies"
            },
            Route53Intent.CDN_DISTRIBUTION: {
                "alias_records": "Use ALIAS records instead of CNAME for apex",
                "health_checks": "Configure health checks for origin servers",
                "caa_records": "Add CAA records for CDN certificates",
                "dnssec": "Enable DNSSEC for content integrity"
            },
            Route53Intent.LOAD_BALANCER: {
                "alias_records": "Prefer ALIAS records for ELB/ALB",
                "health_checks": "Mandatory health checks for backend targets",
                "failover": "Configure failover routing policies",
                "multi_value": "Consider multi-value answer routing"
            },
            Route53Intent.MULTI_REGION: {
                "health_checks": "Essential for multi-region failover",
                "latency_routing": "Use latency-based routing for performance",
                "geolocation": "Consider geolocation routing for compliance",
                "monitoring": "Enhanced monitoring with CloudWatch alarms"
            }
        }
        
        return recommendations.get(intent, {
            "dnssec": "Enable DNSSEC for domain security",
            "query_logging": "Enable query logging for monitoring",
            "health_checks": "Consider health checks for critical records"
        })
