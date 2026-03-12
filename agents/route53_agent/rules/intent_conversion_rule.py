# agents/route53_agent/rules/intent_conversion_rule.py

class IntentConversionRule:
    """
    Rule to handle intent conflicts - when user specifies one intent 
    but hosted zone is configured for another.
    """
    id = "route53_intent_conversion"
    detection = "Hosted zone configuration conflicts with user intent"
    auto_safe = False  # Always manual review for intent conflicts
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = False
        self.fix_type = None
        self.conflict_details = None

    def check_with_intent(self, client, zone_id, zone_name, intent, recommendations):
        """Check for intent vs configuration conflicts."""
        from agents.route53_agent.intent_detector import Route53Intent
        
        conflicts = []
        
        try:
            # Get zone configuration
            response = client.list_resource_record_sets(HostedZoneId=zone_id)
            record_sets = response.get('ResourceRecordSets', [])
            
            has_mx_records = any(r.get('Type') == 'MX' for r in record_sets)
            has_health_checks = any(r.get('HealthCheckId') for r in record_sets)
            has_weighted_routing = any(r.get('Weight') is not None for r in record_sets)
            
            # Check for conflicts based on intent
            if intent == Route53Intent.EMAIL_DOMAIN:
                # User wants email domain but MX records missing
                if not has_mx_records:
                    conflicts.append({
                        "type": "missing_mx_records",
                        "current_config": "No MX records configured",
                        "user_intent": intent.value,
                        "recommendation": "Add MX records for email service"
                    })
            
            elif intent == Route53Intent.MULTI_REGION:
                # User wants multi-region but no routing policies
                if not has_weighted_routing and not has_health_checks:
                    conflicts.append({
                        "type": "missing_routing_policies",
                        "current_config": "No traffic routing policies configured",
                        "user_intent": intent.value,
                        "recommendation": "Configure weighted or geolocation routing"
                    })
            
            elif intent == Route53Intent.LOAD_BALANCER:
                # User wants load balancer setup but no health checks
                if not has_health_checks:
                    conflicts.append({
                        "type": "missing_health_checks",
                        "current_config": "No health checks configured",
                        "user_intent": intent.value,
                        "recommendation": "Add health checks for load balancer endpoints"
                    })
            
        except Exception as e:
            print(f"Error checking intent conflicts for {zone_name}: {e}")
        
        if conflicts:
            self.conflict_details = conflicts
            self._set_conversion_instructions(conflicts[0])
            
            print(f"🐛 DEBUG: IntentConversionRule set fix_instructions: {self.fix_instructions}")
            print(f"🐛 DEBUG: IntentConversionRule set can_auto_fix: {self.can_auto_fix}")
            print(f"🐛 DEBUG: IntentConversionRule set fix_type: {self.fix_type}")
            
            return True
            
        return False

    def _set_conversion_instructions(self, conflict):
        """Set specific instructions based on conflict type."""
        if conflict["type"] == "missing_mx_records":
            self.fix_instructions = [
                f"Current: {conflict['current_config']}",
                f"User Intent: {conflict['user_intent']}",
                "",
                "🔧 Conversion Steps:",
                "1. Determine your email service provider",
                "2. Create MX records pointing to mail servers",
                "3. Add SPF record for sender authentication",
                "4. Configure DKIM for email signing",
                "5. Add DMARC record for email policy",
                "",
                "⚠️ This will configure the domain for email service"
            ]
            self.can_auto_fix = False
            self.fix_type = "configure_email_domain"
            
        elif conflict["type"] == "missing_routing_policies":
            self.fix_instructions = [
                f"Current: {conflict['current_config']}",
                f"User Intent: {conflict['user_intent']}",
                "",
                "🔧 Conversion Steps:",
                "1. Create health checks for each regional endpoint",
                "2. Update DNS records with routing policies",
                "3. Configure weighted routing for traffic distribution",
                "4. Or use geolocation routing for regional routing",
                "5. Or use latency-based routing for performance",
                "",
                "⚠️ This will enable multi-region traffic management"
            ]
            self.can_auto_fix = False
            self.fix_type = "configure_multi_region"
            
        elif conflict["type"] == "missing_health_checks":
            self.fix_instructions = [
                f"Current: {conflict['current_config']}",
                f"User Intent: {conflict['user_intent']}",
                "",
                "🔧 Conversion Steps:",
                "1. Create health checks for load balancer endpoints",
                "2. Configure check interval and failure threshold",
                "3. Associate health checks with DNS records",
                "4. Set up CloudWatch alarms for notifications",
                "",
                "⚠️ This will enable health monitoring for load balancers"
            ]
            self.can_auto_fix = False
            self.fix_type = "add_health_checks"
    
    def check(self, client, zone_id, zone_name):
        """Standard check method (not used for intent-aware rules)."""
        return False
    
    def fix(self, client, zone_id, zone_name):
        """Fix method (requires manual intervention)."""
        print(f"⚠️ Intent conversion requires manual configuration for {zone_name}")
        return False
