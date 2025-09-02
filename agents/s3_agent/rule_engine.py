# agents/s3_agent/rule_engine.py

import yaml

class RuleEngine:
    def __init__(self, rules_file):
        with open(rules_file, "r") as f:
            self.rules = yaml.safe_load(f)

    def detect(self, issues):
        """
        Detect misconfigurations based on predefined rules.        
        issues = [
            {"resource": "my-bucket", "issue": "Bucket allows public read access"},
            {"resource": "logs-bucket", "issue": "Bucket does not have default encryption"},
        ]
        """
        findings = []
        for issue in issues:
            matched = False
            for rule in self.rules:
                pattern = rule["detection"]
                if re.search(pattern, issue["issue"], re.IGNORECASE):
                    findings.append({
                        "service": "s3",
                        "resource": issue["resource"],
                        "issue": issue["issue"],
                        "fix": rule["fix"],
                        "auto_safe": rule["auto_safe"]
                    })
                    matched = True
                    break
            if not matched:
                # no rule hit, let doc_search handle it
                pass
        return findings
