# agents/iam_agent/doc_search.py


class DocSearch:
    def __init__(self):
        # Intent-specific documentation references
        self.intent_docs = {
            "least_privilege": {
                "common_issues": [
                    "Users have admin permissions unnecessarily",
                    "Policies contain wildcard actions (*)",
                    "Missing conditions on sensitive actions",
                    "Direct policy attachments instead of groups",
                    "Overly broad resource specifications"
                ],
                "aws_docs": "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#grant-least-privilege",
                "best_practices": [
                    "Grant minimal permissions required for tasks",
                    "Use managed policies instead of inline policies",
                    "Add conditions to restrict access (MFA, IP, time)",
                    "Use groups for common permission sets",
                    "Regular access reviews and permission audits"
                ]
            },
            "strong_security": {
                "common_issues": [
                    "Users without MFA enabled",
                    "Old access keys not rotated",
                    "Missing password policy requirements",
                    "No session duration limits on roles",
                    "Insufficient logging and monitoring"
                ],
                "aws_docs": "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#enable-mfa",
                "best_practices": [
                    "Enable MFA for all users with console access",
                    "Rotate access keys regularly (90 days max)",
                    "Implement strong password policies",
                    "Set appropriate session durations for roles",
                    "Enable CloudTrail for API activity logging",
                    "Use conditions to enforce security requirements"
                ]
            },
            "service_account": {
                "common_issues": [
                    "Service accounts with unnecessary console access",
                    "Using long-term access keys instead of roles",
                    "Overly permissive trust policies",
                    "Missing source IP or VPC conditions",
                    "Service accounts with human user permissions"
                ],
                "aws_docs": "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use-cases.html",
                "best_practices": [
                    "Use IAM roles instead of access keys when possible",
                    "Restrict trust policies to specific AWS services",
                    "Add source IP or VPC endpoint conditions",
                    "Use minimal permissions for specific services only",
                    "Implement credential rotation automation",
                    "Monitor for unusual API usage patterns"
                ]
            },
            "developer_flexibility": {
                "common_issues": [
                    "Developers with production access unnecessarily",
                    "No separation between dev/staging/production",
                    "Missing time-bound access controls",
                    "Insufficient self-service capabilities",
                    "No sandbox environments for testing"
                ],
                "aws_docs": "https://docs.aws.amazon.com/IAM/latest/UserGuide/tutorial_cross-account-with-roles.html",
                "best_practices": [
                    "Separate development, staging, and production access",
                    "Use cross-account roles for production access",
                    "Implement time-limited access tokens",
                    "Create sandbox environments for experimentation",
                    "Use developer groups for common permissions",
                    "Provide self-service role assumption capabilities"
                ]
            },
            "compliance": {
                "common_issues": [
                    "Insufficient audit logging enabled",
                    "Missing read-only access for auditors",
                    "No approval process for privilege changes",
                    "Inadequate access review procedures",
                    "Missing compliance reporting capabilities"
                ],
                "aws_docs": "https://docs.aws.amazon.com/IAM/latest/UserGuide/tutorial_billing-permissions.html",
                "best_practices": [
                    "Enable comprehensive CloudTrail logging",
                    "Create read-only roles for audit purposes",
                    "Implement approval workflows for privilege changes",
                    "Conduct regular access reviews and certifications",
                    "Document all permission grants and justifications",
                    "Set up automated compliance reporting"
                ]
            },
            "admin_access": {
                "common_issues": [
                    "Too many users with admin permissions",
                    "Admin access without MFA requirements",
                    "No break-glass procedures for emergencies",
                    "Missing monitoring for admin activities",
                    "Permanent admin access instead of temporary"
                ],
                "aws_docs": "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#use-roles-with-cross-account-access",
                "best_practices": [
                    "Minimize number of admin users",
                    "Require MFA for all admin operations",
                    "Use just-in-time access for admin privileges",
                    "Implement break-glass procedures for emergencies",
                    "Monitor and alert on admin activities",
                    "Use multi-person approval for critical changes"
                ]
            },
            "operational_efficiency": {
                "common_issues": [
                    "Manual permission management processes",
                    "Inconsistent access patterns across environments",
                    "Lack of federated identity integration",
                    "No automation for common tasks",
                    "Inefficient cross-account access patterns"
                ],
                "aws_docs": "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers.html",
                "best_practices": [
                    "Implement federated identity providers (SAML, OIDC)",
                    "Use AWS SSO for centralized access management",
                    "Automate role and policy provisioning",
                    "Standardize cross-account access patterns",
                    "Create reusable permission templates",
                    "Implement self-service access request systems"
                ]
            },
            "automation_role": {
                "common_issues": [
                    "Automation roles with excessive permissions",
                    "Missing conditions on automation access",
                    "No separation between CI/CD environments",
                    "Hardcoded credentials in automation",
                    "Insufficient monitoring of automation activities"
                ],
                "aws_docs": "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use-cases.html#id_roles_use-cases_aws-services",
                "best_practices": [
                    "Use minimal permissions for automation tasks",
                    "Separate CI/CD roles by environment (dev/prod)",
                    "Add source IP and time-based conditions",
                    "Use OIDC providers for GitHub Actions/GitLab CI",
                    "Implement credential-free automation workflows",
                    "Monitor automation role usage patterns",
                    "Set up alerts for unusual automation activities"
                ]
            }
        }
    
    def search(self, issue, intent=None):
        """
        Enhanced doc search with intent context.
        
        Args:
            issue: The detected IAM issue
            intent: User's detected intent (e.g., "least_privilege", "service_account")
        """
        if intent and intent in self.intent_docs:
            docs = self.intent_docs[intent]
            
            # Find most relevant issue
            relevant_issue = None
            best_match_score = 0
            
            for common_issue in docs["common_issues"]:
                # Calculate relevance score based on keyword matching
                issue_keywords = set(issue.lower().split())
                common_issue_keywords = set(common_issue.lower().split())
                
                # Find intersection and calculate match score
                matches = len(issue_keywords.intersection(common_issue_keywords))
                match_score = matches / max(len(issue_keywords), len(common_issue_keywords))
                
                if match_score > best_match_score and match_score > 0.2:  # At least 20% match
                    best_match_score = match_score
                    relevant_issue = common_issue
            
            if relevant_issue:
                return {
                    "issue_type": relevant_issue,
                    "intent": intent,
                    "aws_docs": docs["aws_docs"],
                    "best_practices": docs["best_practices"],
                    "suggestion": f"This appears to be a {intent.replace('_', ' ')} issue. {relevant_issue} is a common problem in this scenario.",
                    "match_score": best_match_score
                }
        
        # Enhanced fallback search with IAM-specific categories
        return self._fallback_search(issue)
    
    def _fallback_search(self, issue):
        """Fallback search for issues not covered by intent-specific docs."""
        issue_lower = issue.lower()
        
        # Security-related issues
        security_keywords = ['mfa', 'password', 'access key', 'rotation', 'authentication', 'login']
        if any(keyword in issue_lower for keyword in security_keywords):
            return {
                "category": "security",
                "aws_docs": "https://docs.aws.amazon.com/IAM/latest/UserGuide/security.html",
                "suggestion": "This appears to be a security-related IAM issue. Check AWS security best practices."
            }
        
        # Policy-related issues
        policy_keywords = ['policy', 'permission', 'privilege', 'access denied', 'unauthorized']
        if any(keyword in issue_lower for keyword in policy_keywords):
            return {
                "category": "policies",
                "aws_docs": "https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html",
                "suggestion": "This appears to be a policy-related IAM issue. Review IAM policy documentation."
            }
        
        # Role-related issues
        role_keywords = ['role', 'assume', 'trust policy', 'cross-account', 'service role']
        if any(keyword in issue_lower for keyword in role_keywords):
            return {
                "category": "roles",
                "aws_docs": "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html",
                "suggestion": "This appears to be a role-related IAM issue. Check IAM roles documentation."
            }
        
        # User management issues
        user_keywords = ['user', 'group', 'console access', 'login profile']
        if any(keyword in issue_lower for keyword in user_keywords):
            return {
                "category": "users",
                "aws_docs": "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users.html",
                "suggestion": "This appears to be a user management IAM issue. Review IAM users documentation."
            }
        
        # Generic fallback
        return f"No direct rule found. Refer to AWS IAM Documentation for: {issue}"
    
    def get_security_checklist(self, intent=None):
        """Get a security checklist based on intent."""
        if intent and intent in self.intent_docs:
            return {
                "intent": intent,
                "checklist": self.intent_docs[intent]["best_practices"],
                "common_pitfalls": self.intent_docs[intent]["common_issues"]
            }
        
        # Generic IAM security checklist
        return {
            "intent": "general",
            "checklist": [
                "Enable MFA for all users",
                "Use groups to assign permissions",
                "Grant least privilege access",
                "Rotate access keys regularly",
                "Use roles for applications",
                "Enable CloudTrail logging",
                "Review permissions regularly",
                "Use conditions in policies"
            ],
            "common_pitfalls": [
                "Users with unnecessary admin access",
                "Missing MFA on sensitive accounts",
                "Old unused access keys",
                "Overly broad policies",
                "No access review process"
            ]
        }
    
    def get_remediation_guidance(self, issue_type, intent=None):
        """Get specific remediation guidance for an issue."""
        remediation_guides = {
            "mfa_missing": {
                "steps": [
                    "1. Navigate to IAM > Users > [Username] > Security credentials",
                    "2. In Multi-factor authentication (MFA) section, choose 'Manage'",
                    "3. Select 'Virtual MFA device' for mobile app authentication",
                    "4. Follow setup wizard to scan QR code with authenticator app",
                    "5. Enter two consecutive MFA codes to complete setup"
                ],
                "validation": "Verify MFA is working by signing out and back in",
                "automation": "Consider using AWS CLI or SDK to automate MFA setup for bulk users"
            },
            "access_key_old": {
                "steps": [
                    "1. Create new access key: aws iam create-access-key --user-name [USERNAME]",
                    "2. Update applications to use new access key",
                    "3. Test applications with new key for 24-48 hours",
                    "4. Deactivate old key: aws iam update-access-key --access-key-id [KEY] --status Inactive",
                    "5. Monitor for errors, then delete old key if no issues"
                ],
                "validation": "Confirm all applications work with new key before deleting old one",
                "automation": "Set up automated key rotation using AWS Lambda and Secrets Manager"
            },
            "excessive_permissions": {
                "steps": [
                    "1. Review current permissions using IAM Access Advisor",
                    "2. Identify unused permissions over past 90 days",
                    "3. Create new policy with only required permissions",
                    "4. Test new policy in development environment",
                    "5. Apply new policy and remove excessive permissions"
                ],
                "validation": "Monitor CloudTrail for access denied errors after policy change",
                "automation": "Use AWS Config Rules to detect and alert on excessive permissions"
            }
        }
        
        return remediation_guides.get(issue_type, {
            "steps": ["Refer to AWS documentation for specific remediation steps"],
            "validation": "Test changes in non-production environment first",
            "automation": "Consider automating this fix using AWS Config or Lambda"
        })