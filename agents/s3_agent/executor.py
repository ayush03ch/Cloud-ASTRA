# agents/s3_agent/executor.py

class S3Executor:
    def format_for_fixer(self, findings):
        """
        Normalize findings for FixerAgent consumption.
        Ensures schema consistency.
        """
        normalized = []
        for f in findings:
            # Create proper fix structure based on rule_id
            fix_action = self._get_fix_action(f.get("rule_id"))
            
            normalized.append({
                "service": f.get("service", "s3"),
                "resource": f["resource"],
                "issue": f["issue"],
                "fix": fix_action,
                "auto_safe": f.get("auto_safe", False),
                "note": f.get("note", None),
                "rule_id": f.get("rule_id"),
            })
        return normalized
    
    def _get_fix_action(self, rule_id):
        """Map rule IDs to proper fix actions."""
        if rule_id == "s3_public_access_block":
            return {
                "action": "fix_public_access",
                "params": {}
            }
        else:
            return {
                "action": "manual_review",
                "params": {}
            }