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

    def scan(self):
        """
        Scan all S3 buckets for issues using rules.
        Returns normalized findings.
        """
        findings = []
        buckets = self.client.list_buckets().get("Buckets", [])
        # Step 1: Rules-based detection
        for bucket in buckets:
            bucket_name = bucket["Name"]

            for rule in self.rules:
                try:
                    if rule.check(self.client, bucket_name):
                        findings.append({
                            "service": "s3",
                            "resource": bucket_name,
                            "issue": rule.detection,
                            "rule_id": rule.id,
                            "auto_safe": rule.auto_safe,
                            "source": "rule"
                        })
                except Exception as e:
                    findings.append({
                        "service": "s3",
                        "resource": bucket_name,
                        "issue": f"Error checking rule {rule.id}: {str(e)}",
                        "rule_id": rule.id,
                        "auto_safe": False,
                        "source": "rule_error"
                    })

        # If no findings, try doc search + LLM
        if not findings:
            # Step 2: AWS Docs search
            for bucket in buckets:
                docs = self.doc_search.search("S3 bucket misconfiguration")
                if docs:
                    findings.append({
                        "service": "s3",
                        "resource": bucket["Name"],
                        "issue": "Unknown issue",
                        "note": docs,
                        "rule_id": "doc_ref",
                        "auto_safe": False,
                        "source": "doc_search"
                    })
                else:
                    # Step 3: LLM fallback
                    llm_fix = self.llm_fallback.suggest_fix("S3 bucket unknown error")
                    findings.append({
                        "service": "s3",
                        "resource": bucket["Name"],
                        "issue": "Unknown issue",
                        "fix": llm_fix,
                        "rule_id": "llm_fallback",
                        "auto_safe": False,
                        "source": "llm"
                    })
        # Step 4: Return normalized findings
        return self.executor.format_for_fixer(findings)


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
