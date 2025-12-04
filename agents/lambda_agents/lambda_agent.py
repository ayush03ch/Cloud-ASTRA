# agents/lambda_agents/lambda_agent.py

import boto3
import pkgutil
import importlib
import inspect
from pathlib import Path
import yaml

from agents.lambda_agents.executor import LambdaExecutor

from .doc_search import DocSearch
from .llm_fallback import LLMFallback
from .intent_detector import IntentDetector


class LambdaAgent:
    def __init__(self, client=None, creds=None):
        if client and hasattr(client, 'list_functions'):  
            # If explicitly passed a boto3 client (check it has Lambda methods)
            self.client = client
        elif client and isinstance(client, dict):
            # If first param is actually credentials dict
            self.client = boto3.client(
                "lambda",
                aws_access_key_id=client.get("aws_access_key_id"),
                aws_secret_access_key=client.get("aws_secret_access_key"),
                aws_session_token=client.get("aws_session_token"),
                region_name=client.get("region", "us-east-1"),
            )
        elif creds:  
            # Build boto3 client from creds dict
            self.client = boto3.client(
                "lambda",
                aws_access_key_id=creds.get("aws_access_key_id"),
                aws_secret_access_key=creds.get("aws_secret_access_key"),
                aws_session_token=creds.get("aws_session_token"),
                region_name=creds.get("region", "us-east-1"),
            )
        else:
            # Fallback: default boto3 client (uses local ~/.aws/credentials or env vars)
            self.client = boto3.client("lambda")
            
        self.rules = self._load_rules()
        self.doc_search = DocSearch()
        self.llm_fallback = LLMFallback()
        self.intent_detector = IntentDetector()
        self.executor = LambdaExecutor()

    def _load_rules(self):
        """Dynamically load all rules from the rules directory."""
        rules_dir = Path(__file__).parent / "rules"
        rules = {}
        
        # Get all Python files in rules directory
        rule_files = [f for f in rules_dir.glob("*.py") if f.name != "__init__.py"]
        
        for rule_file in rule_files:
            module_name = rule_file.stem
            module_path = f"agents.lambda_agents.rules.{module_name}"
            
            try:
                module = importlib.import_module(module_path)
                
                # Find all classes that are rules (not the base class)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if hasattr(obj, 'id') and hasattr(obj, 'check'):
                        rules[obj.id] = obj()
            except ImportError as e:
                print(f"Failed to load rule {module_path}: {e}")
        
        return rules

    def analyze(self, function_name=None, region=None, user_intent_input=None):
        """Analyze Lambda function(s) for security issues.
        
        Args:
            function_name: Specific function to analyze (optional)
            region: AWS region (optional)
            user_intent_input: Dict mapping function names to their intents
        """
        try:
            findings = []
            
            # Get functions to analyze
            functions_to_check = []
            
            if function_name:
                try:
                    response = self.client.get_function(FunctionName=function_name)
                    functions_to_check = [response['Configuration']]
                except Exception as e:
                    print(f"Error retrieving Lambda function {function_name}: {e}")
                    return findings
            else:
                # List all functions
                try:
                    paginator = self.client.get_paginator('list_functions')
                    for page in paginator.paginate():
                        functions_to_check.extend(page['Functions'])
                except Exception as e:
                    print(f"Error listing Lambda functions: {e}")
                    return findings
            
            # Run all rules against each function
            for func in functions_to_check:
                func_name = func['FunctionName']
                
                for rule_id, rule in self.rules.items():
                    # Skip intent conversion rules for direct analysis
                    if "intent_conversion" in rule_id:
                        continue
                    
                    try:
                        if rule.check(self.client, func_name):
                            # Detect intent for context - use user input if provided
                            user_intent = None
                            user_description = None
                            
                            if user_intent_input and func_name in user_intent_input:
                                user_intent = user_intent_input[func_name]
                            elif user_intent_input and '_global_intent' in user_intent_input:
                                user_intent = user_intent_input['_global_intent']
                            
                            intent, confidence, reasoning = self.intent_detector.detect_intent(
                                func_name, self.client, user_intent=user_intent, user_description=user_description
                            )
                            
                            finding = {
                                "service": "lambda",
                                "resource": func_name,
                                "issue": rule.detection,
                                "rule_id": rule_id,
                                "intent": intent.value if hasattr(intent, 'value') else str(intent),
                                "intent_confidence": confidence,
                                "intent_reasoning": reasoning,
                                "fix_instructions": getattr(rule, 'fix_instructions', []),
                                "can_auto_fix": getattr(rule, 'can_auto_fix', False),
                                "fix_type": getattr(rule, 'fix_type', None),
                                "auto_safe": getattr(rule, 'auto_safe', False)
                            }
                            
                            # Add fix action if available
                            if hasattr(rule, 'get_fix_action'):
                                finding["fix"] = rule.get_fix_action(func_name)
                            else:
                                # Fallback: create fix action from fix_type
                                fix_type = getattr(rule, 'fix_type', None)
                                if fix_type:
                                    finding["fix"] = {
                                        "action": fix_type,
                                        "params": {"function_name": func_name}
                                    }
                            
                            findings.append(finding)
                    except Exception as e:
                        print(f"Error running rule {rule_id} on {func_name}: {e}")
            
            return findings
        except Exception as e:
            print(f"Error analyzing Lambda functions: {e}")
            return []

    def fix(self, function_name, rule_id):
        """Apply fix for a specific rule on a Lambda function."""
        if rule_id not in self.rules:
            return {"status": "error", "message": f"Rule {rule_id} not found"}
        
        rule = self.rules[rule_id]
        
        if not hasattr(rule, 'fix'):
            return {"status": "error", "message": f"Rule {rule_id} does not support auto-fix"}
        
        try:
            rule.fix(self.client, function_name)
            return {"status": "success", "message": f"Fixed {function_name} with rule {rule_id}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
