# agents/route53_agent/route53_agent.py

import boto3
import pkgutil
import importlib
import inspect
from pathlib import Path
import yaml
import json
from typing import Dict, List, Optional, Any

from agents.route53_agent.executor import Route53Executor
from agents.utils.llm_security_analyzer import LLMSecurityAnalyzer
from agents.utils.rag_security_search import RAGSecuritySearch
from .doc_search import DocSearch
from .llm_fallback import LLMFallback
from .intent_detector import Route53IntentDetector


class Route53Agent:
    def __init__(self, client=None, creds=None):
        if client and hasattr(client, 'list_hosted_zones'):  
            # If explicitly passed a boto3 Route53 client
            self.client = client
        elif client and isinstance(client, dict):
            # If first param is actually credentials dict
            self.client = boto3.client(
                "route53",
                aws_access_key_id=client.get("aws_access_key_id"),
                aws_secret_access_key=client.get("aws_secret_access_key"),
                aws_session_token=client.get("aws_session_token"),
                region_name=client.get("region", "us-east-1"),
            )
        elif creds:  
            # Build boto3 client from creds dict
            self.client = boto3.client(
                "route53",
                aws_access_key_id=creds.get("aws_access_key_id"),
                aws_secret_access_key=creds.get("aws_secret_access_key"),
                aws_session_token=creds.get("aws_session_token"),
                region_name=creds.get("region", "us-east-1"),
            )
        else:
            # Fallback: default boto3 client
            self.client = boto3.client("route53")
            
        # Initialize components
        self.rules = self._load_rules()
        self.doc_search = DocSearch()
        self.llm_fallback = LLMFallback()
        self.intent_detector = Route53IntentDetector()
        self.executor = Route53Executor()
        
        # Initialize new detection tiers
        self.rag_search = RAGSecuritySearch()
        self.llm_analyzer = None
        
        # Initialize LLM only if API key exists
        try:
            self.llm_analyzer = LLMSecurityAnalyzer()
            print("[Route53Agent] ✅ LLM fallback enabled (Gemini)")
        except ValueError as e:
            print(f"[Route53Agent] ⚠️  LLM fallback disabled: {e}")

    def _load_rules(self):
        """Dynamically import all rule classes from rules/ directory."""
        rules = []
        rules_path = Path(__file__).parent / "rules"

        for module_info in pkgutil.iter_modules([str(rules_path)]):
            module_name = f"agents.route53_agent.rules.{module_info.name}"
            module = importlib.import_module(module_name)

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, "check") and hasattr(obj, "fix"):
                    rules.append(obj())
        return rules

    def scan(self, user_intent_input=None, scope="all"):
        """
        Scan Route53 hosted zones for issues using intent-aware rules.
        Returns normalized findings with intent context.
        
        Args:
            user_intent_input: Dict with user's explicit intent per hosted zone
                              e.g., {"Z1234567890ABC": "public_website", "Z0987654321XYZ": "internal_service"}
            scope: "all", "public", "private", or specific hosted zone ID
        """
        findings = []
        
        # Determine scan scope
        zones_to_scan = self._get_scan_zones(scope)
        
        if not zones_to_scan:
            print("⚠️ No hosted zones found to scan")
            return self.executor.format_for_fixer([])
        
        print(f"\n{'='*60}")
        print(f"[Route53Agent] Starting 3-Tier Security Analysis")
        print(f"[Route53Agent] Total hosted zones to scan: {len(zones_to_scan)}")
        print(f"{'='*60}\n")
        
        # Step 1: Intent-aware rules-based detection (TIER 1)
        for zone in zones_to_scan:
            zone_id = zone['Id'].split('/')[-1]  # Extract zone ID from full path
            zone_name = zone['Name']
            
            # Detect intent for this hosted zone
            user_intent = None
            if user_intent_input:
                # Check for zone-specific intent first
                user_intent = user_intent_input.get(zone_id) or user_intent_input.get(zone_name)
                # If no zone-specific intent, check for global intent
                if not user_intent:
                    user_intent = user_intent_input.get('_global_intent')
            
            print(f"DEBUG: user_intent for {zone_name} ({zone_id}) = {user_intent}")
            
            intent, confidence, reasoning = self.intent_detector.detect_intent(
                zone_id, zone_name, self.client, user_intent
            )
            
            print(f"🎯 Intent for {zone_name}: {intent.value} (confidence: {confidence:.2f})")
            print(f"   Reasoning: {reasoning}")
            
            # Get intent-specific recommendations
            recommendations = self.intent_detector.get_intent_recommendations(intent, zone_name)
            
            # Apply rules with intent context
            for rule in self.rules:
                try:
                    # Pass intent context to rule
                    if hasattr(rule, 'check_with_intent'):
                        # Intent-aware rules
                        if rule.id in ["route53_intent_conversion"]:
                            rule.intent_confidence = confidence
                        issue_found = rule.check_with_intent(self.client, zone_id, zone_name, intent, recommendations)
                    else:
                        # Standard rules - pass zone ID and name
                        issue_found = self._call_rule_check(rule, zone_id, zone_name, zone)
                        
                    if issue_found:
                        # Adjust auto_safe based on intent
                        auto_safe = self._should_auto_apply(rule, intent, zone_id, zone_name, zone)
                        
                        # Get rule fix information
                        fix_instructions = getattr(rule, 'fix_instructions', None)
                        can_auto_fix = getattr(rule, 'can_auto_fix', False)
                        fix_type = getattr(rule, 'fix_type', None)
                        
                        # DEBUG: Log for instruction details
                        print(f"DEBUG: Rule {rule.id} - fix_instructions: {fix_instructions}")
                        print(f"DEBUG: Rule {rule.id} - can_auto_fix: {can_auto_fix}")
                        print(f"DEBUG: Rule {rule.id} - fix_type: {fix_type}")
                        print(f"DEBUG: Rule {rule.id} - auto_safe: {auto_safe}")
                        
                        finding = {
                            "service": "route53",
                            "resource": zone_name,
                            "zone_id": zone_id,
                            "issue": getattr(rule, "detection", "Security issue detected"),
                            "rule_id": rule.id,
                            "auto_safe": auto_safe,
                            "fix_instructions": fix_instructions,
                            "can_auto_fix": can_auto_fix,
                            "fix_type": fix_type,
                            "source": "rule",
                            "tier": 1,
                            "intent": intent.value,
                            "intent_confidence": confidence,
                            "is_private": zone.get('Config', {}).get('PrivateZone', False)
                        }
                        findings.append(finding)
                        
                except Exception as e:
                    print(f"⚠️ Error running rule {rule.id} on {zone_name}: {e}")
                    findings.append({
                        "service": "route53",
                        "resource": zone_name,
                        "zone_id": zone_id,
                        "issue": f"Rule {rule.id} encountered an error",
                        "details": str(e),
                        "rule_id": rule.id,
                        "auto_safe": False,
                        "source": "rule_error",
                        "intent": intent.value if 'intent' in locals() else "unknown"
                    })
        
        # Count rule-based findings
        rule_findings_count = sum(1 for f in findings if f.get("source") == "rule")
        print(f"\n[Route53Agent] TIER 1 (Rules): Found {rule_findings_count} total issues")
        
        # TIER 2: RAG-based detection
        print(f"\n[Route53Agent] TIER 2 (RAG): Starting knowledge base search...")
        for zone in zones_to_scan:
            zone_id = zone['Id'].split('/')[-1]
            zone_name = zone['Name']
            
            # Get intent
            user_intent = user_intent_input.get(zone_id) if user_intent_input else None
            if not user_intent and user_intent_input:
                user_intent = user_intent_input.get(zone_name) or user_intent_input.get('_global_intent')
            
            intent, confidence, reasoning = self.intent_detector.detect_intent(zone_id, zone_name, self.client, user_intent)
            
            zone_config = self._get_zone_config(zone_id, zone_name)
            
            rag_findings = self.rag_search.search_security_issues(
                service='route53',
                configuration=zone_config,
                intent=intent.value,
                top_k=5
            )
            
            for rag_finding in rag_findings:
                rag_finding.update({
                    'resource': zone_name,
                    'zone_id': zone_id,
                    'service': 'route53',
                    'source': 'rag',
                    'tier': 2,
                    'intent': intent.value,
                    'intent_confidence': confidence
                })
                findings.append(rag_finding)
        
        rag_findings_count = sum(1 for f in findings if f.get("source") == "rag")
        print(f"[Route53Agent] TIER 2 (RAG): Found {rag_findings_count} additional issues")
        
        # TIER 3: LLM fallback
        if self.llm_analyzer:
            print(f"\n[Route53Agent] TIER 3 (LLM): Starting Gemini analysis...")
            llm_findings_count = 0
            
            for zone in zones_to_scan:
                zone_id = zone['Id'].split('/')[-1]
                zone_name = zone['Name']
                zone_findings = [f for f in findings if f.get("resource") == zone_name]
                
                # Only use LLM if we have < 3 findings for this zone
                if len(zone_findings) < 3:
                    user_intent = user_intent_input.get(zone_id) if user_intent_input else None
                    if not user_intent and user_intent_input:
                        user_intent = user_intent_input.get(zone_name) or user_intent_input.get('_global_intent')
                    
                    intent, confidence, reasoning = self.intent_detector.detect_intent(zone_id, zone_name, self.client, user_intent)
                    
                    zone_config = self._get_zone_config(zone_id, zone_name)
                    
                    llm_findings = self.llm_analyzer.analyze_security_issues(
                        service='route53',
                        resource_name=zone_name,
                        configuration=zone_config,
                        intent=intent.value,
                        user_context=str(user_intent_input) if user_intent_input else ""
                    )
                    
                    for llm_finding in llm_findings:
                        llm_finding.update({
                            'service': 'route53',
                            'zone_id': zone_id,
                            'source': 'llm',
                            'tier': 3,
                            'intent': intent.value,
                            'intent_confidence': confidence,
                            'rule_id': 'llm_fallback'
                        })
                        findings.append(llm_finding)
                        llm_findings_count += 1
                else:
                    print(f"[Route53Agent] TIER 3 (LLM): Skipped {zone_name} - sufficient findings ({len(zone_findings)})")
            
            print(f"[Route53Agent] TIER 3 (LLM): Found {llm_findings_count} additional issues")
        else:
            print(f"[Route53Agent] TIER 3 (LLM): Skipped - Gemini API not configured")
        
        # Deduplicate findings
        findings = self._deduplicate_findings(findings)
        
        print(f"\n{'='*60}")
        print(f"[Route53Agent] Analysis Complete: {len(findings)} unique findings")
        print(f"{'='*60}\n")
        
        # Step 4: Return normalized findings
        return self.executor.format_for_fixer(findings)

    def _get_scan_zones(self, scope):
        """Get hosted zones based on scan scope."""
        try:
            response = self.client.list_hosted_zones()
            all_zones = response.get('HostedZones', [])
            
            if scope == "all":
                return all_zones
            elif scope == "public":
                return [z for z in all_zones if not z.get('Config', {}).get('PrivateZone', False)]
            elif scope == "private":
                return [z for z in all_zones if z.get('Config', {}).get('PrivateZone', False)]
            else:
                # Specific zone ID
                return [z for z in all_zones if scope in z['Id']]
        except Exception as e:
            print(f"Error listing hosted zones: {e}")
            return []

    def _call_rule_check(self, rule, zone_id, zone_name, zone):
        """Call rule check method with appropriate parameters."""
        try:
            # Try different signatures
            if hasattr(rule, 'check_zone'):
                return rule.check_zone(self.client, zone_id, zone_name, zone)
            else:
                return rule.check(self.client, zone_id, zone_name)
        except TypeError:
            # Fallback to just client and zone_id
            try:
                return rule.check(self.client, zone_id)
            except:
                return False

    def _should_auto_apply(self, rule, intent, zone_id, zone_name, zone):
        """Determine if a fix should be auto-applied based on rule and intent."""
        # Never auto-apply for private zones (could break internal DNS)
        if zone.get('Config', {}).get('PrivateZone', False):
            return False
        
        # Check rule's auto_safe flag
        if not getattr(rule, 'auto_safe', False):
            return False
        
        # For intent-aware rules, check confidence
        if hasattr(rule, 'intent_confidence'):
            return rule.intent_confidence >= 0.8
        
        return True

    def _get_zone_config(self, zone_id, zone_name):
        """Get comprehensive configuration for a hosted zone."""
        config = {
            'zone_id': zone_id,
            'zone_name': zone_name,
            'records': [],
            'dnssec_status': None,
            'query_logging': False,
            'record_count': 0
        }
        
        try:
            # Get zone details
            zone_response = self.client.get_hosted_zone(Id=zone_id)
            config['zone_details'] = zone_response.get('HostedZone', {})
            
            # Get DNSSEC status
            try:
                dnssec_response = self.client.get_dnssec(HostedZoneId=zone_id)
                config['dnssec_status'] = dnssec_response.get('Status', {}).get('ServeSignature')
            except:
                config['dnssec_status'] = 'NOT_ENABLED'
            
            # Get record sets
            record_response = self.client.list_resource_record_sets(HostedZoneId=zone_id)
            config['records'] = record_response.get('ResourceRecordSets', [])
            config['record_count'] = len(config['records'])
            
            # Check for query logging
            try:
                query_log_response = self.client.list_query_logging_configs(HostedZoneId=zone_id)
                config['query_logging'] = len(query_log_response.get('QueryLoggingConfigs', [])) > 0
            except:
                config['query_logging'] = False
                
        except Exception as e:
            print(f"Error getting zone config for {zone_name}: {e}")
        
        return config

    def _deduplicate_findings(self, findings):
        """Remove duplicate findings based on resource and issue."""
        seen = set()
        unique_findings = []
        
        for finding in findings:
            # Create unique key from resource and issue
            key = (finding.get('resource'), finding.get('issue'))
            if key not in seen:
                seen.add(key)
                unique_findings.append(finding)
        
        return unique_findings

    def fix(self, zone_id, zone_name, rule_id):
        """Apply fix for a specific rule on a hosted zone."""
        if not self.rules:
            return False
        
        for rule in self.rules:
            if rule.id == rule_id:
                try:
                    return rule.fix(self.client, zone_id, zone_name)
                except Exception as e:
                    print(f"Error applying fix {rule_id} to {zone_name}: {e}")
                    return False
        
        print(f"Rule {rule_id} not found")
        return False
