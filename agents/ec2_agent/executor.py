# agents/ec2_agent/executor.py


class EC2Executor:
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
                fix_action = self._get_fix_action(f.get("rule_id"), f.get("resource"))
            
            normalized.append({
                "service": f.get("service", "ec2"),
                "resource": f["resource"],
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
    
    def _get_fix_action(self, rule_id, instance_id):
        """Map rule IDs to proper fix actions for legacy support."""
        if rule_id == "ec2_open_security_group":
            return {
                "action": "restrict_security_group",
                "params": {
                    "instance_id": instance_id
                }
            }
        elif rule_id == "ec2_unencrypted_ebs":
            return {
                "action": "encrypt_ebs_volume",
                "params": {
                    "instance_id": instance_id
                }
            }
        elif rule_id == "ec2_missing_backups":
            return {
                "action": "create_ebs_snapshots",
                "params": {
                    "instance_id": instance_id
                }
            }
        elif rule_id == "ec2_unused_instance":
            return {
                "action": "stop_unused_instance",
                "params": {
                    "instance_id": instance_id
                }
            }
        elif rule_id == "ec2_oversized_instance":
            return {
                "action": "recommend_right_sizing",
                "params": {
                    "instance_id": instance_id
                }
            }
        elif rule_id == "ec2_missing_monitoring":
            return {
                "action": "enable_cloudwatch_monitoring",
                "params": {
                    "instance_id": instance_id
                }
            }
        elif rule_id == "ec2_intent_conversion":
            return {
                "action": "rule_based_fix",
                "params": {
                    "rule_id": rule_id,
                    "instance_id": instance_id
                }
            }
        else:
            # All other rules default to manual review
            # This includes complex configuration changes and high-risk modifications
            return {
                "action": "manual_review",
                "params": {
                    "rule_id": rule_id,
                    "instance_id": instance_id
                }
            }
    
    def create_remediation_plan(self, findings):
        """Create a structured remediation plan from findings."""
        plan = {
            "total_issues": len(findings),
            "auto_fixable": 0,
            "manual_review": 0,
            "critical_priority": [],
            "high_priority": [],
            "medium_priority": [],
            "low_priority": [],
            "by_intent": {},
            "by_issue_type": {}
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
                "instance_id": finding["resource"],
                "issue": finding["issue"],
                "rule_id": finding.get("rule_id"),
                "auto_safe": finding.get("auto_safe", False),
                "intent": finding.get("intent", "unknown")
            })
            
            # Group by intent
            intent = finding.get("intent", "unknown")
            if intent not in plan["by_intent"]:
                plan["by_intent"][intent] = []
            plan["by_intent"][intent].append(finding["resource"])
            
            # Group by issue type
            rule_id = finding.get("rule_id", "unknown")
            issue_type = self._get_issue_category(rule_id)
            if issue_type not in plan["by_issue_type"]:
                plan["by_issue_type"][issue_type] = 0
            plan["by_issue_type"][issue_type] += 1
        
        return plan
    
    def _determine_priority(self, finding):
        """Determine priority level for a finding."""
        rule_id = finding.get("rule_id", "")
        intent = finding.get("intent", "")
        issue = finding.get("issue", "").lower()
        
        # Critical priority security issues
        critical_rules = [
            "ec2_open_security_group",
            "ec2_unencrypted_ebs",
            "ec2_public_database"
        ]
        
        # Critical keywords in issue description
        critical_keywords = ["exposed", "public", "unencrypted", "vulnerable", "0.0.0.0/0"]
        
        if (rule_id in critical_rules or 
            any(keyword in issue for keyword in critical_keywords)):
            return "critical"
        
        # High priority operational issues
        high_priority_rules = [
            "ec2_missing_backups",
            "ec2_missing_monitoring",
            "ec2_outdated_ami"
        ]
        
        # High priority intents (production systems)
        high_priority_intents = [
            "web_server",
            "database_server",
            "bastion_host"
        ]
        
        if (rule_id in high_priority_rules or 
            intent in high_priority_intents):
            return "high"
        
        # Medium priority cost and performance issues
        medium_priority_rules = [
            "ec2_oversized_instance",
            "ec2_unused_instance",
            "ec2_intent_conversion"
        ]
        
        if rule_id in medium_priority_rules:
            return "medium"
        
        # Default to low priority
        return "low"
    
    def _get_issue_category(self, rule_id):
        """Categorize issues by type."""
        categories = {
            "security": [
                "ec2_open_security_group",
                "ec2_unencrypted_ebs", 
                "ec2_public_database",
                "ec2_missing_patches"
            ],
            "cost_optimization": [
                "ec2_oversized_instance",
                "ec2_unused_instance",
                "ec2_underutilized_instance"
            ],
            "reliability": [
                "ec2_missing_backups",
                "ec2_single_az_deployment",
                "ec2_missing_monitoring"
            ],
            "performance": [
                "ec2_wrong_instance_type",
                "ec2_storage_performance",
                "ec2_network_bottleneck"
            ],
            "operational": [
                "ec2_intent_conversion",
                "ec2_missing_tags",
                "ec2_outdated_ami"
            ]
        }
        
        for category, rules in categories.items():
            if rule_id in rules:
                return category
        
        return "other"
    
    def generate_fix_summary(self, findings):
        """Generate a summary of potential fixes."""
        summary = {
            "security_fixes": [],
            "cost_optimizations": [],
            "reliability_improvements": [],
            "performance_enhancements": [],
            "operational_changes": [],
            "quick_wins": []
        }
        
        for finding in findings:
            rule_id = finding.get("rule_id", "")
            instance_id = finding["resource"]
            intent = finding.get("intent", "")
            
            # Categorize fixes by type
            if rule_id == "ec2_open_security_group":
                summary["security_fixes"].append({
                    "action": "Restrict security group access",
                    "instance": instance_id,
                    "impact": "Significantly improves security posture",
                    "effort": "Low",
                    "priority": "Critical"
                })
            
            elif rule_id == "ec2_unencrypted_ebs":
                summary["security_fixes"].append({
                    "action": "Encrypt EBS volumes",
                    "instance": instance_id,
                    "impact": "Protects data at rest",
                    "effort": "Medium",
                    "priority": "High"
                })
            
            elif rule_id == "ec2_oversized_instance":
                summary["cost_optimizations"].append({
                    "action": "Right-size instance type",
                    "instance": instance_id,
                    "impact": "Reduces compute costs",
                    "effort": "Medium",
                    "priority": "Medium"
                })
            
            elif rule_id == "ec2_unused_instance":
                summary["cost_optimizations"].append({
                    "action": "Stop or terminate unused instance",
                    "instance": instance_id,
                    "impact": "Eliminates waste costs",
                    "effort": "Low",
                    "priority": "Medium"
                })
            
            elif rule_id == "ec2_missing_backups":
                summary["reliability_improvements"].append({
                    "action": "Set up automated backups",
                    "instance": instance_id,
                    "impact": "Improves disaster recovery capability",
                    "effort": "Low",
                    "priority": "High"
                })
            
            elif rule_id == "ec2_missing_monitoring":
                summary["operational_changes"].append({
                    "action": "Enable CloudWatch monitoring",
                    "instance": instance_id,
                    "impact": "Improves visibility and alerting",
                    "effort": "Low",
                    "priority": "Medium"
                })
            
            # Quick wins for auto-safe items
            if finding.get("auto_safe") and finding.get("fix", {}).get("action") != "manual_review":
                summary["quick_wins"].append({
                    "action": finding.get("fix", {}).get("action", "unknown"),
                    "instance": instance_id,
                    "rule_id": rule_id
                })
        
        return summary
    
    def create_execution_order(self, findings):
        """Create optimal execution order for fixes."""
        # Group findings by dependency and risk
        execution_groups = {
            "immediate": [],     # Critical security fixes
            "short_term": [],    # High-impact, low-risk fixes
            "planned": [],       # Medium complexity changes
            "long_term": []      # Complex architectural changes
        }
        
        for finding in findings:
            rule_id = finding.get("rule_id", "")
            auto_safe = finding.get("auto_safe", False)
            priority = self._determine_priority(finding)
            
            # Immediate fixes - critical security issues
            if priority == "critical":
                execution_groups["immediate"].append(finding)
            
            # Short-term fixes - safe and high impact
            elif auto_safe and priority == "high":
                execution_groups["short_term"].append(finding)
            
            # Planned fixes - require coordination
            elif priority in ["high", "medium"]:
                execution_groups["planned"].append(finding)
            
            # Long-term fixes - complex changes
            else:
                execution_groups["long_term"].append(finding)
        
        return execution_groups
    
    def get_instance_recommendations(self, findings):
        """Get instance-specific recommendations based on findings."""
        instance_recommendations = {}
        
        for finding in findings:
            instance_id = finding["resource"]
            intent = finding.get("intent", "unknown")
            rule_id = finding.get("rule_id", "")
            
            if instance_id not in instance_recommendations:
                instance_recommendations[instance_id] = {
                    "intent": intent,
                    "recommendations": [],
                    "security_score": 100,
                    "cost_optimization_potential": "Low",
                    "reliability_score": 100
                }
            
            rec = instance_recommendations[instance_id]
            
            # Add specific recommendations based on rule
            if rule_id == "ec2_open_security_group":
                rec["recommendations"].append("Implement least privilege security groups")
                rec["security_score"] -= 30
            
            elif rule_id == "ec2_oversized_instance":
                rec["recommendations"].append("Right-size instance to match actual usage")
                rec["cost_optimization_potential"] = "High"
            
            elif rule_id == "ec2_missing_backups":
                rec["recommendations"].append("Implement automated backup strategy")
                rec["reliability_score"] -= 25
            
            # Intent-specific recommendations
            if intent == "web_server":
                rec["recommendations"].extend([
                    "Consider using Auto Scaling Group",
                    "Set up Application Load Balancer",
                    "Implement CDN for static content"
                ])
            elif intent == "database_server":
                rec["recommendations"].extend([
                    "Consider migrating to Amazon RDS",
                    "Use memory-optimized instance types",
                    "Set up read replicas for scaling"
                ])
        
        return instance_recommendations
    
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
            
            # Validate instance ID format
            instance_id = finding.get("resource")
            if instance_id and not instance_id.startswith("i-"):
                validation_results["warnings"].append(
                    f"Finding {i}: Instance ID '{instance_id}' doesn't follow expected format"
                )
            
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
            
            # Check intent validity
            valid_intents = [
                "web_server", "database_server", "application_server", 
                "development_testing", "batch_processing", "high_performance_computing",
                "bastion_host", "load_balancer", "microservices", "data_processing",
                "backup_disaster_recovery", "unknown"
            ]
            
            intent = finding.get("intent")
            if intent and intent not in valid_intents:
                validation_results["warnings"].append(
                    f"Finding {i}: Unknown intent '{intent}'"
                )
        
        return validation_results