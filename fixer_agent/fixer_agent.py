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

        # Extract findings from nested structure if needed
        if isinstance(findings, dict):
            # Flatten all findings from all services
            actual_findings = []
            for service, service_findings in findings.items():
                if isinstance(service_findings, list):
                    actual_findings.extend(service_findings)
            findings = actual_findings
        
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
                # Create enhanced pending fix with instructions
                pending_fix = {
                    "resource": finding["resource"],
                    "issue": finding["issue"],
                    "fix_instructions": finding.get("fix_instructions", []),
                    "can_auto_fix": finding.get("can_auto_fix", False),
                    "fix_type": finding.get("fix_type")
                }
                pending_fixes.append(pending_fix)

        return applied_fixes, pending_fixes

    def apply_specific_fix(self, resource: str, fix_type: str) -> Dict:
        """
        Apply a specific type of fix to a resource.
        
        Args:
            resource: The resource name (e.g., bucket name)
            fix_type: Type of fix to apply (e.g., 'public_access_block', 'index_document', 'disable_website_hosting')
        
        Returns:
            Dict with success status and details
        """
        try:
            if fix_type == "public_access_block":
                success = self.executor.fix_public_access_directly(resource)
                return {
                    "success": success,
                    "message": f"Applied public access block to {resource}",
                    "details": ["Enabled public access block", "Removed public bucket policy", "Set ACL to private"]
                }
            
            elif fix_type == "index_document":
                success = self.executor.fix_index_document_directly(resource)
                return {
                    "success": success,
                    "message": f"Fixed index document configuration for {resource}",
                    "details": ["Updated index document to match available files", "Ensured public access for website"]
                }
            
            elif fix_type == "disable_website_hosting":
                success = self.executor.disable_website_hosting_directly(resource)
                return {
                    "success": success,
                    "message": f"Disabled website hosting and secured {resource}",
                    "details": ["Removed website configuration", "Enabled public access block", "Applied private bucket policy"]
                }
            
            elif fix_type == "enable_website_hosting":
                success = self.executor.enable_website_hosting_directly(resource)
                return {
                    "success": success,
                    "message": f"Enabled website hosting for {resource}",
                    "details": ["Configured website hosting", "Set index document", "Enabled public access"]
                }
            
            elif fix_type == "enable_public_access":
                success = self.executor.enable_public_access_directly(resource)
                return {
                    "success": success,
                    "message": f"Enabled public access for website {resource}",
                    "details": ["Configured public access block for website", "Applied public read policy"]
                }
            
            else:
                raise ValueError(f"Unknown fix type: {fix_type}")
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to apply {fix_type} fix to {resource}: {str(e)}",
                "details": []
            }
