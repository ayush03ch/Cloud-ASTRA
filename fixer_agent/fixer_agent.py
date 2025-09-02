# fixer_agent/fixer_agent.py

from typing import List, Dict, Tuple
from .executor import Executor
from .utils import format_finding

class FixerAgent:
    """
    Orchestrates application of fixes across findings.
    """
    def __init__(self, creds: dict):
        self.executor = Executor(creds)

    def apply(self, findings: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Process a list of findings and attempt fixes.
        Returns (applied_fixes, pending_fixes).
        """
        applied_fixes = []
        pending_fixes = []

        for finding in findings:
            if finding.get("auto_safe", False):
                success = self.executor.run(finding)
                applied_fixes.append({
                    "resource": finding["resource"],
                    "issue": finding["issue"],
                    "status": "applied" if success else "failed",
                    "details": format_finding(finding)
                })
            else:
                pending_fixes.append(finding)

        return applied_fixes, pending_fixes
