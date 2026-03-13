# agents/apigateway_agent/executor.py

from typing import Dict, List


class APIGatewayExecutor:
    """Formats API Gateway findings for FixerAgent."""

    def format_for_fixer(self, findings: List[Dict]) -> List[Dict]:
        formatted = []
        for f in findings:
            formatted.append({
                "service":           "apigateway",
                "resource":          f.get("resource", "unknown-api"),
                "api_id":            f.get("api_id", ""),
                "stage_name":        f.get("stage_name", ""),
                "issue":             f.get("issue", "Unknown issue"),
                "severity":          f.get("severity", "medium"),
                "rule_id":           f.get("rule_id", "unknown"),
                "auto_safe":         f.get("auto_safe", False),
                "fix_instructions":  f.get("fix_instructions", []),
                "can_auto_fix":      f.get("can_auto_fix", False),
                "fix_type":          f.get("fix_type"),
                "details":           f.get("details", f.get("description", "")),
                "source":            f.get("source", "rule"),
                "tier":              f.get("tier", 1),
                "intent":            f.get("intent", "unknown"),
                "intent_confidence": f.get("intent_confidence", 0.0),
            })
        return formatted
