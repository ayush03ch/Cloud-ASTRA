# agents/s3_agent/s3_agent.py

import boto3
import pkgutil
import importlib
import inspect
from pathlib import Path
import yaml

from agents.s3_agent.executor import S3Executor
from agents.utils.llm_security_analyzer import LLMSecurityAnalyzer
from agents.utils.rag_security_search import RAGSecuritySearch

from .doc_search import DocSearch
from .llm_fallback import LLMFallback
from .intent_detector import IntentDetector


class S3Agent:
    def __init__(self, client=None, creds=None):
        if client and hasattr(client, 'list_buckets'):  
            # If explicitly passed a boto3 client (check it has S3 methods)
            self.client = client
        elif client and isinstance(client, dict):
            # If first param is actually credentials dict
            self.client = boto3.client(
                "s3",
                aws_access_key_id=client.get("aws_access_key_id"),
                aws_secret_access_key=client.get("aws_secret_access_key"),
                aws_session_token=client.get("aws_session_token"),
                region_name=client.get("region", "us-east-1"),
            )
        elif creds:  
            # Build boto3 client from creds dict
            self.client = boto3.client(
                "s3",
                aws_access_key_id=creds.get("aws_access_key_id"),
                aws_secret_access_key=creds.get("aws_secret_access_key"),
                aws_session_token=creds.get("aws_session_token"),
                region_name=creds.get("region", "us-east-1"),
            )
        else:
            # Fallback: default boto3 client (uses local ~/.aws/credentials or env vars)
            self.client = boto3.client("s3")
            
        self.rules = self._load_rules()
        self.doc_search = DocSearch()
        self.llm_fallback = LLMFallback()
        self.intent_detector = IntentDetector()
        self.executor = S3Executor()
        
        # Initialize new detection tiers
        self.rag_search = RAGSecuritySearch()
        self.llm_analyzer = None
        
        # Initialize LLM only if API key exists
        try:
            self.llm_analyzer = LLMSecurityAnalyzer()
            print("[S3Agent] ✅ LLM fallback enabled (Gemini)")
        except ValueError as e:
            print(f"[S3Agent] ⚠️  LLM fallback disabled: {e}")


    def _load_rules(self):
        """Dynamically import all rule classes from rules/ directory."""
        rules = []
        rules_path = Path(__file__).parent / "rules"

        for module_info in pkgutil.iter_modules([str(rules_path)]):
            module_name = f"agents.s3_agent.rules.{module_info.name}"
            module = importlib.import_module(module_name)

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, "check") and hasattr(obj, "fix"):
                    rules.append(obj())
        return rules

    def scan(self, user_intent_input=None):
        """
        Scan all S3 buckets for issues using intent-aware rules.
        Returns normalized findings with intent context.
        
        Args:
            user_intent_input: Dict with user's explicit intent per bucket
                              e.g., {"bucket1": "website hosting", "bucket2": "data storage"}
        """
        findings = []
        buckets = self.client.list_buckets().get("Buckets", [])
        
        print(f"\n{'='*60}")
        print(f"[S3Agent] Starting 3-Tier Security Analysis")
        print(f"[S3Agent] Total buckets to scan: {len(buckets)}")
        print(f"{'='*60}\n")
        
        # Step 1: Intent-aware rules-based detection (TIER 1)
        for bucket in buckets:
            bucket_name = bucket["Name"]
            
            # Detect intent for this bucket
            # Handle both bucket-specific and global user intent
            user_intent = None
            if user_intent_input:
                # Check for bucket-specific intent first
                user_intent = user_intent_input.get(bucket_name)
                # If no bucket-specific intent, check for global intent
                if not user_intent:
                    user_intent = user_intent_input.get('_global_intent')
            
            print(f"DEBUG: user_intent for {bucket_name} = {user_intent}")
            
            intent, confidence, reasoning = self.intent_detector.detect_intent(
                bucket_name, self.client, user_intent
            )
            
            print(f"🎯 Intent for {bucket_name}: {intent.value} (confidence: {confidence:.2f})")
            print(f"   Reasoning: {reasoning}")
            
            # Get intent-specific recommendations
            recommendations = self.intent_detector.get_intent_recommendations(intent, bucket_name)
            
            # Apply rules with intent context
            for rule in self.rules:
                try:
                    # Pass intent context to rule
                    if hasattr(rule, 'check_with_intent'):
                        # intent-aware rules, pass confidence also
                        if rule.id in ["s3_website_hosting", "s3_intent_conversion"]:
                            rule.intent_confidence = confidence  # Store confidence for auto_safe decision
                        issue_found = rule.check_with_intent(self.client, bucket_name, intent, recommendations)
                    else:
                        # no intent rules
                        issue_found = rule.check(self.client, bucket_name)
                        
                    if issue_found:
                        # Adjust auto_safe based on intent
                        auto_safe = self._should_auto_apply(rule, intent, bucket_name)
                        
                        # Get hardcoded fixed instructions if available
                        fix_instructions = getattr(rule, 'fix_instructions', None)
                        can_auto_fix = getattr(rule, 'can_auto_fix', False)
                        fix_type = getattr(rule, 'fix_type', None)
                        
                        # DEBUG: Log for instruction details
                        print(f"DEBUG: Rule {rule.id} - fix_instructions: {fix_instructions}")
                        print(f"DEBUG: Rule {rule.id} - can_auto_fix: {can_auto_fix}")
                        print(f"DEBUG: Rule {rule.id} - fix_type: {fix_type}")
                        print(f"DEBUG: Rule {rule.id} - auto_safe: {auto_safe}")
                        
                        finding = {
                            "service": "s3",
                            "resource": bucket_name,
                            "issue": rule.detection,
                            "rule_id": rule.id,
                            "auto_safe": auto_safe,
                            "source": "rule",
                            "intent": intent.value,
                            "intent_confidence": confidence,
                            "intent_reasoning": reasoning,
                            "recommendations": recommendations
                        }
                        
                        # Add auto-fix action for auto-safe issues
                        if auto_safe:
                            if rule.id == "s3_public_access_block":
                                finding["fix"] = {
                                    "action": "fix_public_access",
                                    "params": {"bucket_name": bucket_name}
                                }
                            elif rule.id == "s3_unencrypted_bucket":
                                finding["fix"] = {
                                    "action": "put_bucket_encryption",
                                    "params": {
                                        "Bucket": bucket_name,
                                        "ServerSideEncryptionConfiguration": {
                                            "Rules": [{
                                                "ApplyServerSideEncryptionByDefault": {
                                                    "SSEAlgorithm": "AES256"
                                                },
                                                "BucketKeyEnabled": True
                                            }]
                                        }
                                    }
                                }
                            elif rule.id == "s3_website_hosting":
                                finding["fix"] = {
                                    "action": "fix_website_hosting", 
                                    "params": {"bucket_name": bucket_name}
                                }
                            else:
                                # Generic fix - let the rule handle it
                                finding["fix"] = {
                                    "action": "rule_based_fix",
                                    "params": {"rule_id": rule.id, "bucket_name": bucket_name}
                                }
                        
                        # Add fix info when available (for both auto and manual fixes)
                        if fix_instructions:
                            print(f"DEBUG: Adding fix instructions to finding for {bucket_name}")
                            finding.update({
                                "fix_instructions": fix_instructions,
                                "can_auto_fix": can_auto_fix,
                                "fix_type": fix_type
                            })
                        else:
                            print(f"DEBUG: No fix instructions available for {bucket_name}")
                        
                        findings.append(finding)
                except Exception as e:
                    findings.append({
                        "service": "s3",
                        "resource": bucket_name,
                        "issue": f"Error checking rule {rule.id}: {str(e)}",
                        "rule_id": rule.id,
                        "auto_safe": False,
                        "source": "rule_error",
                        "intent": intent.value if 'intent' in locals() else "unknown"
                    })

        # Count rule-based findings
        rule_findings_count = sum(1 for f in findings if f.get("source") == "rule")
        print(f"\n[S3Agent] TIER 1 (Rules): Found {rule_findings_count} total issues across all buckets")
        
        # Step 2: RAG-based detection (TIER 2) - run for each bucket
        print(f"\n[S3Agent] TIER 2 (RAG): Starting knowledge base search...")
        for bucket in buckets:
            bucket_name = bucket["Name"]
            
            # Get intent for this bucket
            user_intent = None
            if user_intent_input:
                user_intent = user_intent_input.get(bucket_name)
                if not user_intent:
                    user_intent = user_intent_input.get('_global_intent')
            
            intent, confidence, reasoning = self.intent_detector.detect_intent(
                bucket_name, self.client, user_intent
            )
            
            # Get bucket configuration for RAG
            bucket_config = self._get_bucket_config(bucket_name)
            
            # Search RAG knowledge base
            rag_findings = self.rag_search.search_security_issues(
                service='s3',
                configuration=bucket_config,
                intent=intent.value,
                top_k=5
            )
            
            for rag_finding in rag_findings:
                rag_finding['resource'] = bucket_name
                rag_finding['service'] = 's3'
                rag_finding['source'] = 'rag'
                rag_finding['tier'] = 2
                rag_finding['intent'] = intent.value
                rag_finding['intent_confidence'] = confidence
                findings.append(rag_finding)
        
        rag_findings_count = sum(1 for f in findings if f.get("source") == "rag")
        print(f"[S3Agent] TIER 2 (RAG): Found {rag_findings_count} additional issues")
        
        # Step 3: LLM fallback (TIER 3) - only for buckets with few findings
        if self.llm_analyzer:
            print(f"\n[S3Agent] TIER 3 (LLM): Starting Gemini analysis...")
            llm_findings_count = 0
            
            for bucket in buckets:
                bucket_name = bucket["Name"]
                
                # Count findings for this specific bucket
                bucket_findings = [f for f in findings if f.get("resource") == bucket_name]
                
                # Only use LLM if we have < 3 findings for this bucket
                if len(bucket_findings) < 3:
                    # Get intent for this bucket
                    user_intent = None
                    if user_intent_input:
                        user_intent = user_intent_input.get(bucket_name)
                        if not user_intent:
                            user_intent = user_intent_input.get('_global_intent')
                    
                    intent, confidence, reasoning = self.intent_detector.detect_intent(
                        bucket_name, self.client, user_intent
                    )
                    
                    # Get full configuration
                    bucket_config = self._get_bucket_config(bucket_name)
                    
                    # Analyze with LLM
                    llm_findings = self.llm_analyzer.analyze_security_issues(
                        service='s3',
                        resource_name=bucket_name,
                        configuration=bucket_config,
                        intent=intent.value,
                        user_context=str(user_intent_input) if user_intent_input else ""
                    )
                    
                    for llm_finding in llm_findings:
                        llm_finding['service'] = 's3'
                        llm_finding['source'] = 'llm'
                        llm_finding['tier'] = 3
                        llm_finding['intent'] = intent.value
                        llm_finding['intent_confidence'] = confidence
                        llm_finding['rule_id'] = 'llm_fallback'
                        findings.append(llm_finding)
                        llm_findings_count += 1
                else:
                    print(f"[S3Agent] TIER 3 (LLM): Skipped {bucket_name} - sufficient findings ({len(bucket_findings)})")
            
            print(f"[S3Agent] TIER 3 (LLM): Found {llm_findings_count} additional issues")
        else:
            print(f"[S3Agent] TIER 3 (LLM): Skipped - Gemini API not configured")
        
        # Deduplicate findings across all tiers
        findings = self._deduplicate_findings(findings)
        
        print(f"\n{'='*60}")
        print(f"[S3Agent] Analysis Complete: {len(findings)} unique findings")
        print(f"{'='*60}\n")
        
        # Step 4: Return normalized findings
        return self.executor.format_for_fixer(findings)

    def _should_auto_apply(self, rule, intent, bucket_name):
        """
        Determine if a rule should be auto-applied based on intent context.
        
        This prevents dangerous auto-fixes like making website buckets private.
        """
        from .intent_detector import S3Intent
        
        # Intent conversion rule - check confidence for explicit user intent
        if rule.id == "s3_intent_conversion":
            rule_confidence = getattr(rule, 'intent_confidence', 0.0)
            print(f"DEBUG: Intent conversion rule confidence: {rule_confidence}")
            if rule_confidence >= 1.0:  # Explicit user intent
                print(f"✅ Explicit user intent ({rule_confidence:.2f}) - auto-enabling intent conversion")
                return True
            else:
                print(f" Intent conversion detected for {bucket_name} - requiring manual review (confidence: {rule_confidence})")
                return False  # Manual review for inferred intent conflicts
        
        # Website hosting intent - be very careful with public access rules
        if intent == S3Intent.WEBSITE_HOSTING:
            if rule.id == "s3_public_access_block":
                print(f" Skipping auto-fix for public access on website bucket: {bucket_name}")
                return False  # Don't auto-block public access for websites
            elif rule.id == "s3_website_hosting":
                # For website hosting, check confidence level
                rule_confidence = getattr(rule, 'intent_confidence', 0.0)
                
                # High confidence (including explicit user intent) = auto-enable
                if rule_confidence >= 0.8:
                    print(f"🚀 High confidence website hosting detected ({rule_confidence:.2f}) - auto-enabling")
                    return True  # Auto-enable for high confidence
                else:
                    # Lower confidence = follow rule's setting
                    rule_auto_safe = getattr(rule, 'auto_safe', False)
                    print(f"DEBUG: Website hosting rule auto_safe setting: {rule_auto_safe}, confidence: {rule_confidence:.2f}")
                    return rule_auto_safe
                
        # Data storage intent - apply security rules
        elif intent in [S3Intent.DATA_STORAGE, S3Intent.DATA_ARCHIVAL, S3Intent.BACKUP_STORAGE]:
            if rule.id == "s3_public_access_block":
                return True   #  auto-block public access for data storage
                
        # For unknown intent, be conservative
        elif intent == S3Intent.UNKNOWN:
            if rule.id == "s3_public_access_block":
                return False  # Don't auto-fix if not sure of intent
                
        # Default to rule's original auto_safe setting
        return rule.auto_safe

    def _get_bucket_config(self, bucket_name: str) -> dict:
        """Collect comprehensive bucket configuration for analysis"""
        config = {'bucket_name': bucket_name}
        
        try:
            config['encryption'] = self.client.get_bucket_encryption(Bucket=bucket_name)
        except Exception:
            config['encryption'] = None
        
        try:
            config['public_access_block'] = self.client.get_public_access_block(Bucket=bucket_name)
        except Exception:
            config['public_access_block'] = None
        
        try:
            config['versioning'] = self.client.get_bucket_versioning(Bucket=bucket_name)
        except Exception:
            config['versioning'] = None
        
        try:
            config['logging'] = self.client.get_bucket_logging(Bucket=bucket_name)
        except Exception:
            config['logging'] = None
        
        try:
            config['policy'] = self.client.get_bucket_policy(Bucket=bucket_name)
        except Exception:
            config['policy'] = None
        
        try:
            config['acl'] = self.client.get_bucket_acl(Bucket=bucket_name)
        except Exception:
            config['acl'] = None
        
        try:
            config['website'] = self.client.get_bucket_website(Bucket=bucket_name)
        except Exception:
            config['website'] = None
        
        try:
            config['lifecycle'] = self.client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
        except Exception:
            config['lifecycle'] = None
        
        try:
            config['tags'] = self.client.get_bucket_tagging(Bucket=bucket_name)
        except Exception:
            config['tags'] = None
        
        return config

    def _deduplicate_findings(self, findings: list) -> list:
        """Remove duplicate findings across detection tiers (prefer rules > rag > llm)"""
        seen = {}
        unique = []
        
        # Sort by tier (prefer lower tier numbers = rules first)
        for finding in sorted(findings, key=lambda x: x.get('tier', 0)):
            # Create key from resource + issue (normalized)
            resource = finding.get('resource', '')
            issue = finding.get('issue', '').lower().strip()
            key = (resource, issue)
            
            if key not in seen:
                seen[key] = True
                unique.append(finding)
            else:
                source = finding.get('source', 'unknown')
                print(f"[S3Agent] Dedup: Skipping duplicate from {source} - {issue}")
        
        return unique


    def apply_fix(self, finding):
        """
        Apply fix if auto_safe is True, else recommend manual review.
        """
        for rule in self.rules:
            if rule.id == finding.get("rule_id"):
                if finding.get("auto_safe"):
                    try:
                        rule.fix(self.client, finding["resource"])
                        return f"✅ Applied fix for {rule.id} on {finding['resource']}"
                    except Exception as e:
                        return f"❌ Failed to fix {rule.id} on {finding['resource']}: {str(e)}"
                else:
                    return f" Fix for {rule.id} requires manual approval"
        return " Rule not found or handled by doc/LLM"
