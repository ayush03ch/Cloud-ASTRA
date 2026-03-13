# agents/cloudfront_agent/doc_search.py

class DocSearch:
    def search(self, query, intent=None):
        return {
            "source": "CloudFront Security Best Practices",
            "documentation_link": "https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/security.html",
            "relevant_content": (
                "Enable HTTPS redirect, associate a WAF WebACL, enable access logging, "
                "and enforce TLS 1.2+ for all CloudFront distributions."
            ),
        }
