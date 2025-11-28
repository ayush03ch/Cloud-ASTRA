# agents/iam_agent/executor.py


class IAMExecutor:
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
                fix_action = self._get_fix_action(f.get("rule_id"), f.get("resource"), f.get("resource_type"))
            
            normalized.append({
                "service": f.get("service", "iam"),
                "resource": f["resource"],
                "resource_type": f.get("resource_type", "user"),
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
    
    def _get_fix_action(self, rule_id, resource_name, resource_type):
        """Map rule IDs to proper fix actions for legacy support."""
        if rule_id == "iam_mfa_enforcement":
            return {
                "action": "enforce_mfa",
                "params": {
                    "resource_name": resource_name,
                    "resource_type": resource_type
                }
            }
        elif rule_id == "iam_access_key_rotation":
            return {
                "action": "deactivate_unused_keys",
                "params": {
                    "user_name": resource_name
                }
            }
        elif rule_id == "iam_inactive_user":
            return {
                "action": "disable_inactive_user",
                "params": {
                    "user_name": resource_name,
                    "fix_option": "disable"
                }
            }
        elif rule_id == "iam_least_privilege":
            return {
                "action": "add_mfa_conditions",
                "params": {
                    "resource_name": resource_name,
                    "resource_type": resource_type
                }
            }
        elif rule_id == "iam_intent_conversion":
            return {
                "action": "rule_based_fix",
                "params": {
                    "rule_id": rule_id,
                    "resource_name": resource_name,
                    "resource_type": resource_type
                }
            }
        else:
            # All other rules default to manual review
            # This includes complex policy changes and high-risk modifications
            return {
                "action": "manual_review",
                "params": {
                    "rule_id": rule_id,
                    "resource_name": resource_name,
                    "resource_type": resource_type
                }
            }
    
    def create_remediation_plan(self, findings):
        """Create a structured remediation plan from findings."""
        plan = {
            "total_issues": len(findings),
            "auto_fixable": 0,
            "manual_review": 0,
            "high_priority": [],
            "medium_priority": [],
            "low_priority": [],
            "by_resource_type": {},
            "by_intent": {}
        }
        
        for finding in findings:
            # Count auto-fixable vs manual
            if finding.get("auto_safe"):
                plan["auto_fixable"] += 1
            else:
                plan["manual_review"] += 1
            
            # Categorize by priority based on rule and intent
            priority = self._determine_priority(finding)
            plan[f"{priority}_priority"].append({
                "resource": finding["resource"],
                "resource_type": finding.get("resource_type", "user"),
                "issue": finding["issue"],
                "rule_id": finding.get("rule_id"),
                "auto_safe": finding.get("auto_safe", False),
                "intent": finding.get("intent", "unknown")
            })
            
            # Group by resource type
            resource_type = finding.get("resource_type", "user")
            if resource_type not in plan["by_resource_type"]:
                plan["by_resource_type"][resource_type] = []
            plan["by_resource_type"][resource_type].append(finding["resource"])
            
            # Group by intent
            intent = finding.get("intent", "unknown")
            if intent not in plan["by_intent"]:
                plan["by_intent"][intent] = 0
            plan["by_intent"][intent] += 1
        
        return plan
    
    def _determine_priority(self, finding):
        """Determine priority level for a finding."""
        rule_id = finding.get("rule_id", "")
        intent = finding.get("intent", "")
        
        # High priority security issues
        high_priority_rules = [
            "iam_mfa_enforcement",
            "iam_least_privilege",  
            "iam_access_key_rotation"
        ]
        
        # High priority intents
        high_priority_intents = [
            "admin_access",
            "strong_security"
        ]
        
        if (rule_id in high_priority_rules or 
            intent in high_priority_intents or
            "admin" in finding.get("issue", "").lower()):
            return "high"
        
        # Medium priority operational issues
        medium_priority_rules = [
            "iam_inactive_user",
            "iam_intent_conversion"
        ]
        
        if rule_id in medium_priority_rules:
            return "medium"
        
        # Default to low priority
        return "low"
    
    def generate_fix_summary(self, findings):
        """Generate a summary of potential fixes."""
        summary = {
            "quick_fixes": [],
            "security_improvements": [],
            "compliance_actions": [],
            "cost_optimizations": [],
            "operational_improvements": []
        }
        
        for finding in findings:
            rule_id = finding.get("rule_id", "")
            intent = finding.get("intent", "")
            resource = finding["resource"]
            
            # Categorize fixes by type
            if rule_id == "iam_mfa_enforcement":
                summary["security_improvements"].append({
                    "action": "Enable MFA",
                    "resource": resource,
                    "impact": "Significantly improves account security",
                    "effort": "Low"
                })
            
            elif rule_id == "iam_access_key_rotation":
                summary["security_improvements"].append({
                    "action": "Rotate old access keys",
                    "resource": resource,
                    "impact": "Reduces credential compromise risk",
                    "effort": "Medium"
                })
            
            elif rule_id == "iam_inactive_user":
                summary["cost_optimizations"].append({
                    "action": "Disable inactive users",
                    "resource": resource,
                    "impact": "Reduces attack surface and management overhead",
                    "effort": "Low"
                })
            
            elif rule_id == "iam_least_privilege":
                summary["compliance_actions"].append({
                    "action": "Implement least privilege access",
                    "resource": resource,
                    "impact": "Improves compliance posture",
                    "effort": "High"
                })
            
            elif rule_id == "iam_intent_conversion":
                summary["operational_improvements"].append({
                    "action": "Align configuration with intent",
                    "resource": resource,
                    "impact": "Improves operational clarity",
                    "effort": "Medium"
                })
            
            # Quick fixes for auto-safe items
            if finding.get("auto_safe"):
                summary["quick_fixes"].append({
                    "action": finding.get("fix", {}).get("action", "unknown"),
                    "resource": resource,
                    "rule_id": rule_id
                })
        
        return summary
    
    def create_execution_order(self, findings):
        """Create optimal execution order for fixes."""
        # Group findings by dependency and risk
        execution_groups = {
            "immediate": [],    # High-impact, low-risk fixes
            "short_term": [],   # Medium impact fixes
            "long_term": []     # Complex changes requiring planning
        }
        
        for finding in findings:
            rule_id = finding.get("rule_id", "")
            auto_safe = finding.get("auto_safe", False)
            
            # Immediate fixes - safe and high impact
            if auto_safe and rule_id in ["iam_mfa_enforcement", "iam_inactive_user", "iam_access_key_rotation"]:
                execution_groups["immediate"].append(finding)
            
            # Short-term fixes - require some planning
            elif rule_id in ["iam_intent_conversion"] or not auto_safe:
                execution_groups["short_term"].append(finding)
            
            # Long-term fixes - complex policy changes
            else:
                execution_groups["long_term"].append(finding)
        
        return execution_groups
    
    def validate_findings(self, findings):
        """Validate findings format and completeness."""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "total_findings": len(findings)
        }
        
        required_fields = ["service", "resource", "issue", "rule_id"]
        
        for i, finding in enumerate(findings):
            # Check required fields
            for field in required_fields:
                if field not in finding or finding[field] is None:
                    validation_results["errors"].append(
                        f"Finding {i}: Missing required field '{field}'"
                    )
                    validation_results["valid"] = False
            
            # Check fix action format
            fix_action = finding.get("fix")
            if fix_action and not isinstance(fix_action, dict):
                validation_results["errors"].append(
                    f"Finding {i}: 'fix' field must be a dictionary"
                )
                validation_results["valid"] = False
            elif fix_action and "action" not in fix_action:
                validation_results["warnings"].append(
                    f"Finding {i}: 'fix' action missing 'action' field"
                )
            
            # Check resource type
            if "resource_type" not in finding:
                validation_results["warnings"].append(
                    f"Finding {i}: Missing 'resource_type' field, defaulting to 'user'"
                )
        
        return validation_results
