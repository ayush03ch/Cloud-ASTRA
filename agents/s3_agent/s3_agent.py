# agents/s3_agent/s3_agent.py

import boto3
import pkgutil
import importlib
import inspect
from pathlib import Path
import yaml

from agents.s3_agent.executor import S3Executor

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
        
        # Step 1: Intent-aware rules-based detection
        for bucket in buckets:
            bucket_name = bucket["Name"]
            
            # Detect intent for this bucket
            user_intent = user_intent_input.get(bucket_name) if user_intent_input else None
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
                        # New intent-aware rules
                        issue_found = rule.check_with_intent(self.client, bucket_name, intent, recommendations)
                    else:
                        # Legacy rules - run normally but consider intent in auto_safe decision
                        issue_found = rule.check(self.client, bucket_name)
                        
                    if issue_found:
                        # Adjust auto_safe based on intent
                        auto_safe = self._should_auto_apply(rule, intent, bucket_name)
                        
                        findings.append({
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
                        })
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

        # If no rule-based findings, try doc search + LLM with intent context
        if not any(f["source"] == "rule" for f in findings):
            for bucket in buckets:
                bucket_name = bucket["Name"]
                
                # Get intent if not already detected
                if not any(f["resource"] == bucket_name for f in findings):
                    user_intent = user_intent_input.get(bucket_name) if user_intent_input else None
                    intent, confidence, reasoning = self.intent_detector.detect_intent(
                        bucket_name, self.client, user_intent
                    )
                
                # Step 2: Intent-aware doc search
                docs = self.doc_search.search(f"S3 bucket {intent.value} misconfiguration", intent.value)
                if docs and isinstance(docs, dict):  # Enhanced docs with intent context
                    findings.append({
                        "service": "s3",
                        "resource": bucket_name,
                        "issue": f"Potential {intent.value} configuration issue",
                        "note": docs,
                        "rule_id": "doc_ref",
                        "auto_safe": False,
                        "source": "doc_search",
                        "intent": intent.value,
                        "intent_confidence": confidence
                    })
                elif docs:  # Simple string response
                    findings.append({
                        "service": "s3",
                        "resource": bucket_name,
                        "issue": f"Potential {intent.value} configuration issue",
                        "note": docs,
                        "rule_id": "doc_ref",
                        "auto_safe": False,
                        "source": "doc_search",
                        "intent": intent.value,
                        "intent_confidence": confidence
                    })
                else:
                    # Step 3: Intent-aware LLM fallback
                    llm_fix = self.llm_fallback.suggest_fix(
                        f"S3 bucket {intent.value} configuration issue", 
                        intent.value, 
                        bucket_name
                    )
                    findings.append({
                        "service": "s3",
                        "resource": bucket_name,
                        "issue": f"Unknown {intent.value} issue",
                        "fix": llm_fix,
                        "rule_id": "llm_fallback",
                        "auto_safe": False,
                        "source": "llm",
                        "intent": intent.value,
                        "intent_confidence": confidence
                    })
                    
        # Step 4: Return normalized findings
        return self.executor.format_for_fixer(findings)

    def _should_auto_apply(self, rule, intent, bucket_name):
        """
        Determine if a rule should be auto-applied based on intent context.
        
        This prevents dangerous auto-fixes like making website buckets private.
        """
        from .intent_detector import S3Intent
        
        # Website hosting intent - be very careful with public access rules
        if intent == S3Intent.WEBSITE_HOSTING:
            if rule.id == "s3_public_access_block":
                print(f"⚠️ Skipping auto-fix for public access on website bucket: {bucket_name}")
                return False  # Don't auto-block public access for websites
            elif rule.id == "s3_website_hosting":
                return True   # Do auto-fix website hosting issues
                
        # Data storage intent - apply security rules
        elif intent in [S3Intent.DATA_STORAGE, S3Intent.DATA_ARCHIVAL, S3Intent.BACKUP_STORAGE]:
            if rule.id == "s3_public_access_block":
                return True   # Do auto-block public access for data storage
                
        # For unknown intent, be conservative
        elif intent == S3Intent.UNKNOWN:
            if rule.id == "s3_public_access_block":
                return False  # Don't auto-fix if we're not sure of intent
                
        # Default to rule's original auto_safe setting
        return rule.auto_safe


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
                    return f"⚠️ Fix for {rule.id} requires manual approval"
        return "⚠️ Rule not found or handled by doc/LLM"
