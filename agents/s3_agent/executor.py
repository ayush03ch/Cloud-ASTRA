# agents/s3_agent/executor.py

class S3Executor:
    def format_for_fixer(self, findings):
        """
        Normalize findings for FixerAgent consumption.
        Ensures schema consistency while preserving auto-fix actions.
        """
        normalized = []
        for f in findings:
            # Use existing fix action if provided, otherwise create default
            fix_action = f.get("fix")
            if not fix_action:
                fix_action = self._get_fix_action(f.get("rule_id"))
            
            normalized.append({
                "service": f.get("service", "s3"),
                "resource": f["resource"],
                "issue": f["issue"],
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
                "fix_type": f.get("fix_type")
            })
        return normalized
    
    def _get_fix_action(self, rule_id):
        """Map rule IDs to proper fix actions for legacy support."""
        if rule_id == "s3_public_access_block":
            return {
                "action": "fix_public_access",
                "params": {}
            }
        elif rule_id == "s3_website_hosting":
            return {
                "action": "fix_website_hosting",
                "params": {}
            }
        elif rule_id == "s3_unencrypted_bucket":
            return {
                "action": "rule_based_fix",
                "params": {"rule_id": rule_id, "bucket_name": ""}
            }
        else:
            # All other rules default to manual review
            # This includes s3_versioning_disabled and other cost-related fixes
            return {
                "action": "manual_review",
                "params": {}
            }