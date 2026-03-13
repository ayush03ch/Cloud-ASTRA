# agents/apigateway_agent/doc_search.py

class DocSearch:
    """Documentation references for API Gateway security best practices."""

    def search(self, query: str, intent: str = None) -> dict:
        return {
            "query": query,
            "intent": intent,
            "recommendation": "Enable access logging, enforce TLS, and use usage plans to protect APIs",
            "documentation_link": "https://docs.aws.amazon.com/apigateway/latest/developerguide/security-best-practices.html"
        }
