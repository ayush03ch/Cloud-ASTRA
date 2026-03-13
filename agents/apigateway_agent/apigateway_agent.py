# agents/apigateway_agent/apigateway_agent.py

import boto3
import importlib
import inspect
from pathlib import Path

from agents.apigateway_agent.executor import APIGatewayExecutor
from agents.utils.llm_security_analyzer import LLMSecurityAnalyzer
from agents.utils.rag_security_search import RAGSecuritySearch
from .doc_search import DocSearch
from .llm_fallback import LLMFallback
from .intent_detector import APIGatewayIntentDetector


class APIGatewayAgent:
    def __init__(self, client=None, creds=None):
        self.creds = None
        if client and hasattr(client, 'get_rest_apis'):
            self.client = client
        elif client and isinstance(client, dict):
            self.creds = client
            self.client = boto3.client(
                "apigateway",
                aws_access_key_id=client.get("aws_access_key_id"),
                aws_secret_access_key=client.get("aws_secret_access_key"),
                aws_session_token=client.get("aws_session_token"),
                region_name=client.get("region", "us-east-1"),
            )
        elif creds:
            self.creds = creds
            self.client = boto3.client(
                "apigateway",
                aws_access_key_id=creds.get("aws_access_key_id"),
                aws_secret_access_key=creds.get("aws_secret_access_key"),
                aws_session_token=creds.get("aws_session_token"),
                region_name=creds.get("region", "us-east-1"),
            )
        else:
            self.client = boto3.client("apigateway")

        self.rules           = self._load_rules()
        self.doc_search      = DocSearch()
        self.llm_fallback    = LLMFallback()
        self.intent_detector = APIGatewayIntentDetector()
        self.executor        = APIGatewayExecutor()
        self.rag_search      = RAGSecuritySearch()
        self.llm_analyzer    = None

        try:
            self.llm_analyzer = LLMSecurityAnalyzer()
            print("[APIGatewayAgent] ✅ LLM fallback enabled (Gemini)")
        except ValueError as e:
            print(f"[APIGatewayAgent] ⚠️  LLM fallback disabled: {e}")

    def _list_rest_apis(self, client):
        """List all REST APIs for a specific regional API Gateway client."""
        items = []
        position = None
        while True:
            kwargs = {}
            if position:
                kwargs["position"] = position
            response = client.get_rest_apis(**kwargs)
            items.extend(response.get("items", []))
            position = response.get("position")
            if not position:
                break
        return items

    def _load_rules(self):
        rules = []
        rules_path = Path(__file__).parent / "rules"
        for rule_file in rules_path.glob("*.py"):
            if rule_file.name == "__init__.py":
                continue
            module_name = f"agents.apigateway_agent.rules.{rule_file.stem}"
            try:
                module = importlib.import_module(module_name)
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if hasattr(obj, "check") and hasattr(obj, "id"):
                        rules.append(obj())
            except Exception as e:
                print(f"Failed to load rule {module_name}: {e}")
        return rules

    def scan(self, user_intent_input=None, scope="all"):
        """Scan API Gateway REST APIs for security issues."""
        findings = self.analyze(user_intent_input=user_intent_input, scope=scope)
        return self.executor.format_for_fixer(findings)

    def analyze(self, user_intent_input=None, scope="all"):
        findings = []

        # Collect REST APIs in selected region first
        selected_region = self.client.meta.region_name or "us-east-1"
        api_entries = []
        try:
            all_apis = self._list_rest_apis(self.client)
            api_entries = [(selected_region, self.client, api) for api in all_apis]
        except Exception as e:
            print(f"[APIGatewayAgent] Error listing REST APIs: {e}")
            all_apis = []

        # If region has no APIs and scope is all, discover across regions.
        if not api_entries and scope == "all" and self.creds:
            session = boto3.session.Session()
            regions = session.get_available_regions("apigateway")
            for region in regions:
                if region == selected_region:
                    continue
                try:
                    regional_client = boto3.client(
                        "apigateway",
                        aws_access_key_id=self.creds.get("aws_access_key_id"),
                        aws_secret_access_key=self.creds.get("aws_secret_access_key"),
                        aws_session_token=self.creds.get("aws_session_token"),
                        region_name=region,
                    )
                    regional_apis = self._list_rest_apis(regional_client)
                    if regional_apis:
                        api_entries.extend((region, regional_client, api) for api in regional_apis)
                except Exception:
                    continue

        if scope != "all":
            api_entries = [
                (region, regional_client, api)
                for (region, regional_client, api) in api_entries
                if api["id"] == scope or api["name"] == scope
            ]

        print(f"\n{'='*60}")
        print(f"[APIGatewayAgent] Starting Security Analysis")
        print(f"[APIGatewayAgent] Selected region: {selected_region}")
        print(f"[APIGatewayAgent] Total APIs to scan: {len(api_entries)}")
        print(f"{'='*60}\n")

        for region, regional_client, api in api_entries:
            api_id   = api["id"]
            api_name = api["name"]

            # Detect intent
            user_intent = None
            if user_intent_input:
                user_intent = (
                    user_intent_input.get(api_id)
                    or user_intent_input.get(api_name)
                    or user_intent_input.get("_global_intent")
                )

            intent, confidence, reasoning = self.intent_detector.detect_intent(
                api_id, api_name, user_intent=user_intent
            )

            # Get deployed stages
            try:
                stages = regional_client.get_stages(restApiId=api_id).get("item", [])
            except Exception as e:
                print(f"[APIGatewayAgent] Error fetching stages for {api_id}: {e}")
                stages = []

            if not stages:
                # Some checks are API-level (not stage-level), run with a dummy stage
                stages = [{"stageName": "__api_level__"}]

            for stage in stages:
                stage_name  = stage.get("stageName", "")
                resource_id = f"{region}:{api_name}/{stage_name}" if stage_name != "__api_level__" else f"{region}:{api_name}"

                for rule in self.rules:
                    try:
                        # Rules that only need api_id (default_endpoint_rule)
                        triggered = rule.check(regional_client, api_id, stage_name)
                    except TypeError:
                        triggered = False
                    except Exception as e:
                        print(f"[APIGatewayAgent] Rule {rule.id} error on {resource_id}: {e}")
                        triggered = False

                    if triggered:
                        findings.append({
                            "service":           "apigateway",
                            "resource":          resource_id,
                            "api_id":            api_id,
                            "stage_name":        stage_name,
                            "region":            region,
                            "issue":             rule.detection,
                            "rule_id":           rule.id,
                            "intent":            intent.value,
                            "intent_confidence": confidence,
                            "intent_reasoning":  reasoning,
                            "fix_instructions":  getattr(rule, "fix_instructions", []),
                            "can_auto_fix":      getattr(rule, "can_auto_fix", False),
                            "fix_type":          getattr(rule, "fix_type", None),
                            "auto_safe":         getattr(rule, "auto_safe", False),
                            "severity":          "high",
                            "source":            "rule",
                            "tier":              1,
                        })

        print(f"[APIGatewayAgent] Found {len(findings)} issue(s)")
        return findings
