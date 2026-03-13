# agents/cloudfront_agent/cloudfront_agent.py

import boto3
import pkgutil
import importlib
import inspect
from pathlib import Path

from agents.cloudfront_agent.executor import CloudFrontExecutor
from agents.utils.llm_security_analyzer import LLMSecurityAnalyzer
from agents.utils.rag_security_search import RAGSecuritySearch
from .doc_search import DocSearch
from .llm_fallback import LLMFallback
from .intent_detector import CloudFrontIntentDetector


class CloudFrontAgent:
    def __init__(self, client=None, creds=None):
        if client and hasattr(client, 'list_distributions'):
            self.client = client
        elif client and isinstance(client, dict):
            self.client = boto3.client(
                "cloudfront",
                aws_access_key_id=client.get("aws_access_key_id"),
                aws_secret_access_key=client.get("aws_secret_access_key"),
                aws_session_token=client.get("aws_session_token"),
                region_name=client.get("region", "us-east-1"),
            )
        elif creds:
            self.client = boto3.client(
                "cloudfront",
                aws_access_key_id=creds.get("aws_access_key_id"),
                aws_secret_access_key=creds.get("aws_secret_access_key"),
                aws_session_token=creds.get("aws_session_token"),
                region_name=creds.get("region", "us-east-1"),
            )
        else:
            self.client = boto3.client("cloudfront")

        self.rules = self._load_rules()
        self.doc_search = DocSearch()
        self.llm_fallback = LLMFallback()
        self.intent_detector = CloudFrontIntentDetector()
        self.executor = CloudFrontExecutor()

        self.rag_search = RAGSecuritySearch()
        self.llm_analyzer = None
        try:
            self.llm_analyzer = LLMSecurityAnalyzer()
            print("[CloudFrontAgent] ✅ LLM fallback enabled (Gemini)")
        except ValueError as e:
            print(f"[CloudFrontAgent] ⚠️  LLM fallback disabled: {e}")

    def _load_rules(self):
        rules = []
        rules_path = Path(__file__).parent / "rules"
        for module_info in pkgutil.iter_modules([str(rules_path)]):
            module_name = f"agents.cloudfront_agent.rules.{module_info.name}"
            module = importlib.import_module(module_name)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, "check") and hasattr(obj, "fix"):
                    rules.append(obj())
        return rules

    def _get_distributions(self, scope):
        distributions = []
        try:
            paginator = self.client.get_paginator('list_distributions')
            for page in paginator.paginate():
                items = page.get('DistributionList', {}).get('Items', [])
                distributions.extend(items)
        except Exception as e:
            print(f"[CloudFrontAgent] Error listing distributions: {e}")
        if scope and scope != 'all':
            distributions = [d for d in distributions if d['Id'] == scope]
        return distributions

    def scan(self, user_intent_input=None, scope="all"):
        """Scan CloudFront distributions for security issues."""
        findings = []
        distributions = self._get_distributions(scope)

        if not distributions:
            print("[CloudFrontAgent] ⚠️ No distributions found to scan")
            return self.executor.format_for_fixer([])

        print(f"\n{'='*60}")
        print(f"[CloudFrontAgent] Scanning {len(distributions)} distribution(s)")
        print(f"{'='*60}\n")

        for dist in distributions:
            dist_id = dist['Id']
            domain = dist.get('DomainName', dist_id)
            intent = self.intent_detector.detect_intent(dist_id, domain, self.client)

            for rule in self.rules:
                try:
                    if rule.check(self.client, dist_id, dist):
                        findings.append({
                            "service": "cloudfront",
                            "resource": domain,
                            "distribution_id": dist_id,
                            "issue": rule.detection,
                            "rule_id": rule.id,
                            "severity": getattr(rule, "severity", "medium"),
                            "auto_safe": rule.auto_safe,
                            "can_auto_fix": rule.can_auto_fix,
                            "fix_type": rule.fix_type,
                            "fix_instructions": rule.fix_instructions,
                            "source": "rules",
                            "tier": 1,
                            "intent": intent,
                        })
                except Exception as e:
                    print(f"[CloudFrontAgent] Rule {rule.id} error on {dist_id}: {e}")

        return self.executor.format_for_fixer(findings)
