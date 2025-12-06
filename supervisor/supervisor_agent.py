# supervisor/supervisor_agent.py

import json
import logging
from flask import Flask, request, jsonify
from supervisor.role_manager import assume_role
from supervisor.dispatcher import Dispatcher
from fixer_agent.fixer_agent import FixerAgent

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

class SupervisorAgent:
    def __init__(self, role_arn: str, external_id: str, region: str):
        self.role_arn = role_arn
        self.external_id = external_id
        self.region = region
        self.creds = None

    def assume(self):
        """Assume the given role and store credentials."""
        self.creds = assume_role(self.role_arn, self.external_id, self.region)
        logging.info(f"Assumed role: {self.role_arn}")
        return self.creds

    def scan_and_fix(self, user_intent_input=None, service=None, ec2_filters=None, ec2_checks=None, iam_scope=None, iam_checks=None):
        """Run dispatcher scans and apply fixes with FixerAgent.
        
        Args:
            user_intent_input: Dict with user's explicit intent
            service: Specific service to scan ('s3', 'ec2', 'iam', or None for all)
            ec2_filters: Dict with EC2 instance filters (instance_ids, tags)
            ec2_checks: Dict with EC2 security checks to perform
            iam_scope: Scope for IAM scan ('account', 'users', 'roles', 'policies')
            iam_checks: Dict with IAM security checks to perform
        """
        if not self.creds:
            raise RuntimeError("Must call assume() before scan_and_fix()")

        dispatcher = Dispatcher(self.creds)
        findings = dispatcher.dispatch(
            user_intent_input=user_intent_input,
            service=service,
            ec2_filters=ec2_filters,
            ec2_checks=ec2_checks,
            iam_scope=iam_scope,
            iam_checks=iam_checks
        )
        logging.info(f"Findings: {json.dumps(findings, indent=2)}")

        # Count total issues found
        total_findings = 0
        auto_fixable_count = 0
        
        # Flatten and count findings
        if isinstance(findings, dict):
            for service_name, service_findings in findings.items():
                if isinstance(service_findings, list):
                    total_findings += len(service_findings)
                    auto_fixable_count += sum(1 for f in service_findings if f.get("auto_safe", False))
        
        logging.info(f"Total findings: {total_findings}, Auto-fixable: {auto_fixable_count}")

        # Apply fixes using FixerAgent
        fixer = FixerAgent(self.creds)
        applied_fixes, pending_fixes = fixer.apply(findings)

        # Log the results
        logging.info(f"Auto-fixes applied: {len(applied_fixes)}")
        logging.info(f"Pending manual fixes: {len(pending_fixes)}")

        return {
            "findings": findings,
            "auto_fixes_applied": applied_fixes,
            "pending_fixes": pending_fixes,
            "summary": {
                "total_findings": total_findings,
                "auto_fixable": auto_fixable_count,
                "fixes_applied": len(applied_fixes),
                "pending_manual": len(pending_fixes)
            }
        }

    def apply_manual_fix(self, resource, fix_type):
        """Apply a specific manual fix for a resource."""
        if not self.creds:
            raise RuntimeError("Must call assume() before apply_manual_fix()")

        fixer = FixerAgent(self.creds)
        result = fixer.apply_specific_fix(resource, fix_type)
        
        return result

# ---- Flask API Layer ----
@app.route("/assume", methods=["POST"])
def assume_and_scan():
    """
    Expected JSON input:
    {
        "role_arn": "arn:aws:iam::123456789012:role/TargetRole",
        "external_id": "my-s3-agent-2025",
        "region": "us-east-1"
    }
    """
    try:
        data = request.get_json()
        agent = SupervisorAgent(
            role_arn=data["role_arn"],
            external_id=data["external_id"],
            region=data["region"]
        )
        agent.assume()
        results = agent.scan_and_fix()

        return jsonify({"status": "success", **results})

    except Exception as e:
        logging.error(f"Error in /assume: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
