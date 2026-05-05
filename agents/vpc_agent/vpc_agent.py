# agents/vpc_agent/vpc_agent.py

import boto3
import pkgutil
import importlib
import inspect
from pathlib import Path

from agents.vpc_agent.executor import VPCExecutor
from agents.utils.llm_security_analyzer import LLMSecurityAnalyzer
from agents.utils.rag_security_search import RAGSecuritySearch
from .doc_search import DocSearch
from .llm_fallback import LLMFallback
from .intent_detector import VPCIntentDetector


class VPCAgent:
    def __init__(self, client=None, creds=None):
        if client and hasattr(client, 'describe_vpcs'):
            self.client = client
        elif client and isinstance(client, dict):
            self.client = boto3.client(
                "ec2",
                aws_access_key_id=client.get("aws_access_key_id"),
                aws_secret_access_key=client.get("aws_secret_access_key"),
                aws_session_token=client.get("aws_session_token"),
                region_name=client.get("region", "us-east-1"),
            )
        elif creds:
            self.client = boto3.client(
                "ec2",
                aws_access_key_id=creds.get("aws_access_key_id"),
                aws_secret_access_key=creds.get("aws_secret_access_key"),
                aws_session_token=creds.get("aws_session_token"),
                region_name=creds.get("region", "us-east-1"),
            )
        else:
            self.client = boto3.client("ec2")

        self.rules = self._load_rules()
        self.doc_search = DocSearch()
        self.llm_fallback = LLMFallback()
        self.intent_detector = VPCIntentDetector()
        self.executor = VPCExecutor()

        self.rag_search = RAGSecuritySearch()
        self.llm_analyzer = None
        try:
            self.llm_analyzer = LLMSecurityAnalyzer()
            print("[VPCAgent] ✅ LLM fallback enabled (Gemini)")
        except ValueError as e:
            print(f"[VPCAgent] ⚠️  LLM fallback disabled: {e}")

    def _load_rules(self):
        rules = []
        rules_path = Path(__file__).parent / "rules"
        for module_info in pkgutil.iter_modules([str(rules_path)]):
            module_name = f"agents.vpc_agent.rules.{module_info.name}"
            module = importlib.import_module(module_name)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, "check") and hasattr(obj, "fix"):
                    rules.append(obj())
        return rules

    def _get_vpcs(self, scope):
        vpcs = []
        try:
            paginator = self.client.get_paginator('describe_vpcs')
            for page in paginator.paginate():
                vpcs.extend(page.get('Vpcs', []))
        except Exception as e:
            print(f"[VPCAgent] Error listing VPCs: {e}")
        if scope and scope != 'all':
            vpcs = [v for v in vpcs if v['VpcId'] == scope]
        return vpcs

    def scan(self, user_intent_input=None, scope="all"):
        """Scan VPCs for security issues."""
        findings = []
        vpcs = self._get_vpcs(scope)

        if not vpcs:
            print("[VPCAgent] ⚠️ No VPCs found to scan")
            return self.executor.format_for_fixer([])

        print(f"\n{'='*60}")
        print(f"[VPCAgent] Scanning {len(vpcs)} VPC(s)")
        print(f"{'='*60}\n")

        for vpc in vpcs:
            vpc_id = vpc['VpcId']
            name_tag = next(
                (t['Value'] for t in vpc.get('Tags', []) if t['Key'] == 'Name'),
                vpc_id,
            )
            is_default = vpc.get('IsDefault', False)
            intent = self.intent_detector.detect_intent(vpc_id, name_tag, is_default)
            # Tier 1: deterministic rule checks
            tier1_found = False
            for rule in self.rules:
                try:
                    if rule.check(self.client, vpc_id, vpc):
                        tier1_found = True
                        findings.append({
                            "service": "vpc",
                            "resource": name_tag,
                            "vpc_id": vpc_id,
                            "issue": rule.detection,
                            "rule_id": rule.id,
                            "severity": getattr(rule, "severity", "medium"),
                            "auto_safe": getattr(rule, "auto_safe", False),
                            "can_auto_fix": getattr(rule, "can_auto_fix", False),
                            "fix_type": getattr(rule, "fix_type", None),
                            "fix_instructions": getattr(rule, "fix_instructions", []),
                            "source": "rules",
                            "tier": 1,
                            "intent": intent,
                        })
                except Exception as e:
                    print(f"[VPCAgent] Rule {getattr(rule, 'id', '<unknown>')} error on {vpc_id}: {e}")

            # Tier 2: RAG / doc-based contextual checks (only if no tier1 findings for this VPC)
            rag_results = []
            if not tier1_found and self.rag_search and getattr(self.rag_search, 'enabled', False):
                try:
                    rag_results = self.rag_search.search_security_issues(
                        service="ec2", configuration=vpc, intent=intent, top_k=3
                    )
                    for doc in rag_results:
                        findings.append({
                            "service": "vpc",
                            "resource": name_tag,
                            "vpc_id": vpc_id,
                            "issue": doc.get("title") or doc.get("doc_id"),
                            "rule_id": doc.get("doc_id"),
                            "severity": "medium",
                            "auto_safe": False,
                            "can_auto_fix": False,
                            "fix_type": None,
                            "fix_instructions": [s for s in doc.get("sections", {}).keys()] or [doc.get("title")],
                            "source": "rag",
                            "tier": 2,
                            "intent": intent,
                            "description": next(iter(doc.get("sections", {}).values()), ""),
                        })
                except Exception as e:
                    print(f"[VPCAgent] RAG search failed for {vpc_id}: {e}")

            # Tier 3: LLM fallback (only if nothing found by rules or RAG and analyzer enabled)
            if not tier1_found and not rag_results and self.llm_analyzer:
                try:
                    llm_findings = self.llm_analyzer.analyze_security_issues(
                        service="ec2",
                        resource_name=name_tag,
                        configuration=vpc,
                        intent=intent,
                        user_context=user_intent_input or "",
                    )
                    for lf in llm_findings:
                        findings.append({
                            "service": "vpc",
                            "resource": name_tag,
                            "vpc_id": vpc_id,
                            "issue": lf.get("issue"),
                            "rule_id": lf.get("detection_method", "llm"),
                            "severity": lf.get("severity", "medium"),
                            "auto_safe": lf.get("auto_safe", False),
                            "can_auto_fix": lf.get("can_auto_fix", False),
                            "fix_type": None,
                            "fix_instructions": lf.get("fix_instructions", []),
                            "source": "llm",
                            "tier": 3,
                            "intent": intent,
                            "description": lf.get("description", ""),
                        })
                except Exception as e:
                    print(f"[VPCAgent] LLM analysis failed for {vpc_id}: {e}")

        return self.executor.format_for_fixer(findings)
