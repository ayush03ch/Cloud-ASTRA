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

    def scan_and_fix(self, user_intent_input=None):
        """Run dispatcher scans and apply fixes with FixerAgent."""
        if not self.creds:
            raise RuntimeError("Must call assume() before scan_and_fix()")

        dispatcher = Dispatcher(self.creds)
        findings = dispatcher.dispatch(user_intent_input=user_intent_input)
        logging.info(f"Findings: {json.dumps(findings, indent=2)}")

        fixer = FixerAgent(self.creds)
        applied_fixes, pending_fixes = fixer.apply(findings)

        return {
            "findings": findings,
            "auto_fixes_applied": applied_fixes,
            "pending_fixes": pending_fixes,
        }

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
