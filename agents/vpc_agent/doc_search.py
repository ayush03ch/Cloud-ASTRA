# agents/vpc_agent/doc_search.py

class DocSearch:
    def search(self, query, intent=None):
        return {
            "source": "VPC Security Best Practices",
            "documentation_link": "https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-best-practices.html",
            "relevant_content": (
                "Enable VPC flow logs, avoid using the default VPC in production, "
                "lock down default security groups, and restrict NACL rules."
            ),
        }
