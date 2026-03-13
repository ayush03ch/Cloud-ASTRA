# agents/vpc_agent/intent_detector.py

class VPCIntentDetector:
    def detect_intent(self, vpc_id, name, is_default):
        if is_default:
            return 'default_vpc'
        name_lower = name.lower()
        if any(k in name_lower for k in ['prod', 'production']):
            return 'production'
        if any(k in name_lower for k in ['dev', 'development', 'test', 'staging']):
            return 'non_production'
        return 'general'
