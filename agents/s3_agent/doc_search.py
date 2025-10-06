# agents/s3_agent/doc_search.py

class DocSearch:
    def __init__(self):
        # Intent-specific documentation references
        self.intent_docs = {
            "website_hosting": {
                "common_issues": [
                    "Website endpoint not accessible",
                    "403 Forbidden errors on website",
                    "Missing index document configuration",
                    "Public read access not configured"
                ],
                "aws_docs": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html",
                "best_practices": [
                    "Enable static website hosting",
                    "Configure index and error documents", 
                    "Set up public read policy for objects",
                    "Configure Public Access Block appropriately"
                ]
            },
            "data_storage": {
                "common_issues": [
                    "Data exposed publicly",
                    "Missing encryption at rest",
                    "No versioning enabled",
                    "Incorrect storage class for access pattern"
                ],
                "aws_docs": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html",
                "best_practices": [
                    "Block all public access",
                    "Enable default encryption",
                    "Enable versioning for data protection",
                    "Use appropriate storage classes"
                ]
            },
            "data_archival": {
                "common_issues": [
                    "Using expensive storage class for archival",
                    "No lifecycle policies configured",
                    "Missing MFA delete protection"
                ],
                "aws_docs": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-and-other-bucket-config.html",
                "best_practices": [
                    "Use GLACIER or DEEP_ARCHIVE storage classes",
                    "Configure lifecycle transitions",
                    "Enable MFA delete for protection"
                ]
            }
        }
    
    def search(self, issue, intent=None):
        """
        Enhanced doc search with intent context.
        
        Args:
            issue: The detected issue
            intent: User's detected intent (e.g., "website_hosting", "data_storage")
        """
        if intent and intent in self.intent_docs:
            docs = self.intent_docs[intent]
            
            # Find most relevant issue
            relevant_issue = None
            for common_issue in docs["common_issues"]:
                if any(keyword in issue.lower() for keyword in common_issue.lower().split()):
                    relevant_issue = common_issue
                    break
            
            if relevant_issue:
                return {
                    "issue_type": relevant_issue,
                    "intent": intent,
                    "aws_docs": docs["aws_docs"],
                    "best_practices": docs["best_practices"],
                    "suggestion": f"This appears to be a {intent} bucket. {relevant_issue} is a common issue."
                }
        
        # Fallback to generic search
        return f"No direct rule found. Refer to AWS Docs for: {issue}"