# agents/lambda_agents/executor.py

class LambdaExecutor:
    def format_for_fixer(self, findings):
        """
        Normalize findings for FixerAgent consumption.
        Ensures schema consistency while preserving auto-fix actions.
        """
        normalized = []
        for f in findings:
            # Handle different finding formats from different tiers
            # Rules have 'issue', RAG has 'title', LLM has 'issue'
            issue = f.get("issue") or f.get("title") or f.get("description") or "Unknown issue"
            
            # Skip findings without required fields
            if not f.get("resource"):
                continue
            
            # Use existing fix action if provided, otherwise create default
            fix_action = f.get("fix")
            if not fix_action:
                fix_action = self._get_fix_action(f.get("rule_id"))
            
            normalized.append({
                "service": f.get("service", "lambda"),
                "resource": f["resource"],
                "issue": issue,
                "fix": fix_action,
                "auto_safe": f.get("auto_safe", False),
                "note": f.get("note", None),
                "rule_id": f.get("rule_id"),
                # Preserve additional metadata
                "intent": f.get("intent"),
                "intent_confidence": f.get("intent_confidence"),
                "intent_reasoning": f.get("intent_reasoning"),
                "fix_instructions": f.get("fix_instructions"),
                "can_auto_fix": f.get("can_auto_fix"),
                "fix_type": f.get("fix_type"),
                "source": f.get("source"),
                "tier": f.get("tier"),
                "severity": f.get("severity"),
                "description": f.get("description")
            })
        return normalized
    
    def _get_fix_action(self, rule_id):
        """Map rule IDs to proper fix actions for legacy support."""
        if rule_id == "lambda_logging_disabled":
            return {
                "action": "enable_logging",
                "params": {}
            }
        elif rule_id == "lambda_env_vars_unencrypted":
            return {
                "action": "encrypt_environment_variables",
                "params": {}
            }
        elif rule_id == "lambda_timeout_excessive":
            return {
                "action": "adjust_timeout",
                "params": {"timeout": 30}
            }
        elif rule_id == "lambda_memory_low":
            return {
                "action": "adjust_memory",
                "params": {"memory": 256}
            }
        else:
            return {
                "action": "rule_based_fix",
                "params": {"rule_id": rule_id, "function_name": ""}
            }
