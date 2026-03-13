# agents/apigateway_agent/intent_detector.py

from enum import Enum
from typing import Tuple


class APIGatewayIntent(Enum):
    PUBLIC_API      = "public_api"
    INTERNAL_API    = "internal_api"
    PARTNER_API     = "partner_api"
    MOBILE_BACKEND  = "mobile_backend"
    WEBHOOK         = "webhook"
    UNKNOWN         = "unknown"


class APIGatewayIntentDetector:
    """Detects the purpose/intent of an API Gateway REST API."""

    def __init__(self):
        self.keyword_map = {
            APIGatewayIntent.PUBLIC_API:     ["public", "open", "external", "website", "portal"],
            APIGatewayIntent.INTERNAL_API:   ["internal", "private", "corp", "intranet", "vpc"],
            APIGatewayIntent.PARTNER_API:    ["partner", "b2b", "integration", "third-party"],
            APIGatewayIntent.MOBILE_BACKEND: ["mobile", "app", "ios", "android", "backend"],
            APIGatewayIntent.WEBHOOK:        ["webhook", "event", "callback", "notification", "trigger"],
        }

    def detect_intent(
        self,
        api_id: str,
        api_name: str,
        user_intent: str = None
    ) -> Tuple[APIGatewayIntent, float, str]:
        if user_intent:
            for intent, keywords in self.keyword_map.items():
                if any(kw in user_intent.lower() for kw in keywords):
                    return intent, 1.0, f"User specified: {user_intent}"

        name_lower = api_name.lower()
        for intent, keywords in self.keyword_map.items():
            if any(kw in name_lower for kw in keywords):
                return intent, 0.75, f"Inferred from API name: {api_name}"

        return APIGatewayIntent.PUBLIC_API, 0.4, "Defaulting to public_api (could not infer)"
