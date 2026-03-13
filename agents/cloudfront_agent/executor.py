# agents/cloudfront_agent/executor.py

class CloudFrontExecutor:
    def format_for_fixer(self, findings):
        normalized = []
        for f in findings:
            issue = f.get("issue") or f.get("title") or "Unknown issue"
            if not f.get("resource"):
                continue
            normalized.append({
                "service": "cloudfront",
                "resource": f["resource"],
                "distribution_id": f.get("distribution_id", ""),
                "issue": issue,
                "severity": f.get("severity", "medium"),
                "rule_id": f.get("rule_id"),
                "auto_safe": f.get("auto_safe", False),
                "can_auto_fix": f.get("can_auto_fix", False),
                "fix_type": f.get("fix_type"),
                "fix_instructions": f.get("fix_instructions", []),
                "source": f.get("source", "rules"),
                "tier": f.get("tier", 1),
                "intent": f.get("intent", "unknown"),
                "description": f.get("description", ""),
            })
        return normalized
