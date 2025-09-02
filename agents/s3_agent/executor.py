# agents/s3_agent/executor.py

class S3Executor:
    def format_for_fixer(self, findings):
        """
        Normalize findings for FixerAgent consumption.
        Ensures schema consistency.
        """
        normalized = []
        for f in findings:
            normalized.append({
                "service": f.get("service", "s3"),
                "resource": f["resource"],
                "issue": f["issue"],
                "fix": f.get("fix", {"action": "manual_review", "params": {}}),
                "auto_safe": f.get("auto_safe", False),
                "note": f.get("note", None),
            })
        return normalized