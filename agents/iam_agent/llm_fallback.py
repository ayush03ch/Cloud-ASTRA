# agents/iam_agent/llm_fallback.py


class LLMFallback:
    def suggest_fix(self, issue, intent=None, resource_name=None, resource_type=None):
        """
        Enhanced LLM fallback with intent context for IAM resources.
        
        Args:
            issue: The detected IAM issue
            intent: User's detected intent (e.g., "least_privilege", "service_account")
            resource_name: Name of the IAM resource for context
            resource_type: Type of resource (user, role, policy)
        """
        # Intent-aware fix suggestions
        if intent == "least_privilege":
            return {
                "service": "iam",
                "issue": f"Least privilege issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Review and minimize permissions, replace wildcards with specific actions, add MFA conditions to sensitive operations"
                },
                "auto_safe": False,
                "intent_context": f"{resource_type.title()} '{resource_name}' should follow least privilege principle",
                "recommended_actions": [
                    "Audit current permissions using Access Advisor",
                    "Remove unused permissions from policies", 
                    "Add conditions to restrict access scope",
                    "Use managed policies instead of inline policies"
                ]
            }
        
        elif intent == "strong_security":
            return {
                "service": "iam",
                "issue": f"Security issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Enable MFA, rotate old access keys, add security conditions, and implement monitoring"
                },
                "auto_safe": False,
                "intent_context": f"{resource_type.title()} '{resource_name}' requires strong security controls",
                "recommended_actions": [
                    "Enable MFA for all console users",
                    "Rotate access keys older than 90 days",
                    "Add IP and time-based conditions",
                    "Enable CloudTrail logging for monitoring"
                ]
            }
        
        elif intent == "service_account":
            return {
                "service": "iam", 
                "issue": f"Service account issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Use IAM roles instead of users for services, restrict trust policies, add source conditions"
                },
                "auto_safe": False,
                "intent_context": f"{resource_type.title()} '{resource_name}' appears to be for service/application use",
                "recommended_actions": [
                    "Convert to IAM role if currently a user",
                    "Restrict trust policy to specific AWS services",
                    "Add source IP or VPC endpoint conditions",
                    "Remove console access if not needed",
                    "Use minimal service-specific permissions"
                ]
            }
        
        elif intent == "developer_flexibility":
            return {
                "service": "iam",
                "issue": f"Developer access issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Separate dev/prod environments, use time-bound access, provide sandbox permissions"
                },
                "auto_safe": False,
                "intent_context": f"{resource_type.title()} '{resource_name}' is for development use",
                "recommended_actions": [
                    "Create separate dev/staging/prod access patterns",
                    "Use cross-account roles for production access",
                    "Implement time-limited access tokens",
                    "Provide self-service role assumption capabilities"
                ]
            }
        
        elif intent == "compliance":
            return {
                "service": "iam",
                "issue": f"Compliance issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Enable audit logging, create read-only access, implement approval workflows"
                },
                "auto_safe": False,
                "intent_context": f"{resource_type.title()} '{resource_name}' is for compliance/audit purposes",
                "recommended_actions": [
                    "Enable comprehensive CloudTrail logging",
                    "Create read-only roles for audit purposes",
                    "Document all permission grants",
                    "Set up regular access reviews",
                    "Implement approval workflows for changes"
                ]
            }
        
        elif intent == "admin_access":
            return {
                "service": "iam",
                "issue": f"Admin access issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Require MFA for admin operations, use just-in-time access, implement break-glass procedures"
                },
                "auto_safe": False,
                "intent_context": f"{resource_type.title()} '{resource_name}' has administrative privileges",
                "recommended_actions": [
                    "Require MFA for all admin operations",
                    "Implement just-in-time access elevation",
                    "Set up break-glass procedures for emergencies",
                    "Monitor and alert on admin activities",
                    "Use multi-person approval for critical changes"
                ]
            }
        
        elif intent == "automation_role":
            return {
                "service": "iam",
                "issue": f"Automation role issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Use minimal permissions for automation, separate CI/CD environments, implement credential-free workflows"
                },
                "auto_safe": False,
                "intent_context": f"{resource_type.title()} '{resource_name}' is for automation/CI-CD",
                "recommended_actions": [
                    "Use minimal permissions for automation tasks",
                    "Separate CI/CD roles by environment",
                    "Use OIDC providers for GitHub Actions/GitLab CI",
                    "Add source IP and time-based conditions",
                    "Monitor automation role usage patterns"
                ]
            }
        
        elif intent == "operational_efficiency":
            return {
                "service": "iam",
                "issue": f"Operational issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Implement federated identity, automate permission management, standardize access patterns"
                },
                "auto_safe": False,
                "intent_context": f"{resource_type.title()} '{resource_name}' is for operational efficiency",
                "recommended_actions": [
                    "Implement federated identity providers",
                    "Use AWS SSO for centralized access",
                    "Automate role and policy provisioning",
                    "Standardize cross-account access patterns",
                    "Create self-service access request systems"
                ]
            }
        
        else:
            # Fallback for unknown intent
            return {
                "service": "iam",
                "issue": issue,
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Manual review required - intent unclear. Follow IAM security best practices."
                },
                "auto_safe": False,
                "intent_context": f"{resource_type.title()} '{resource_name}' intent is unclear",
                "recommended_actions": [
                    "Review IAM best practices documentation",
                    "Analyze resource usage patterns",
                    "Consult with resource owner about intended purpose",
                    "Apply least privilege principle as default"
                ]
            }
    
    def get_quick_fixes(self, resource_type, intent=None):
        """Get quick fix suggestions based on resource type and intent."""
        quick_fixes = {
            "user": {
                "least_privilege": [
                    "Remove direct policy attachments, use groups instead",
                    "Replace AWS managed PowerUser/Admin policies",
                    "Add MFA conditions to sensitive policies"
                ],
                "strong_security": [
                    "Enable MFA on console access",
                    "Rotate access keys older than 90 days", 
                    "Set strong password policy requirements"
                ],
                "service_account": [
                    "Convert to IAM role instead of user",
                    "Remove console login profile",
                    "Use application-specific permissions only"
                ]
            },
            "role": {
                "service_account": [
                    "Restrict trust policy to specific AWS services",
                    "Add source VPC or IP conditions",
                    "Use minimal service permissions"
                ],
                "automation_role": [
                    "Add source IP conditions for CI/CD systems",
                    "Separate dev/prod automation roles",
                    "Use OIDC instead of long-term credentials"
                ],
                "admin_access": [
                    "Add MFA condition to assume role policy",
                    "Set maximum session duration to 1 hour",
                    "Require approval for role assumption"
                ]
            },
            "policy": {
                "least_privilege": [
                    "Remove wildcard actions (*)",
                    "Add resource-specific ARNs",
                    "Include condition blocks for access control"
                ],
                "compliance": [
                    "Add detailed conditions for audit requirements",
                    "Include time-based access restrictions",
                    "Add required tags conditions"
                ]
            }
        }
        
        return quick_fixes.get(resource_type, {}).get(intent, [
            f"No specific quick fixes available for {resource_type} with {intent} intent"
        ])
    
    def get_security_recommendations(self, issue_type):
        """Get security recommendations for specific issue types."""
        recommendations = {
            "excessive_permissions": {
                "immediate": "Review and remove unnecessary permissions",
                "short_term": "Implement regular permission audits",
                "long_term": "Automate permission management with AWS Config"
            },
            "missing_mfa": {
                "immediate": "Enable MFA for all console users",
                "short_term": "Enforce MFA through IAM policies",
                "long_term": "Integrate with corporate identity provider"
            },
            "old_access_keys": {
                "immediate": "Rotate keys older than 90 days",
                "short_term": "Implement automated key rotation",
                "long_term": "Use IAM roles instead of access keys"
            },
            "weak_trust_policy": {
                "immediate": "Add conditions to trust policy",
                "short_term": "Regular trust policy reviews",
                "long_term": "Implement policy as code practices"
            }
        }
        
        return recommendations.get(issue_type, {
            "immediate": "Review issue and apply security best practices",
            "short_term": "Document and monitor the configuration",
            "long_term": "Automate security compliance checks"
        })
