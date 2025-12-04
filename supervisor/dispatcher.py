# supervisor/dispatcher.py
from agents.s3_agent.s3_agent import S3Agent
from agents.lambda_agents.lambda_agent import LambdaAgent

class Dispatcher:
    """
    Sends tasks to appropriate service agents.
    Supports S3 and Lambda agents.
    Routes based on resource types in user_intent_input or explicit service selection.
    """

    def __init__(self, creds, service=None):
        self.creds = creds
        self.service = service  # Explicit service selection from UI

    def dispatch(self, user_intent_input=None):
        results = {}
        
        # Determine which services to scan based on user_intent_input
        services_to_scan = self._determine_services(user_intent_input)
        
        # Run S3 Agent if S3 resources are being scanned
        if 's3' in services_to_scan:
            s3_agent = S3Agent(creds=self.creds)
            results["s3"] = s3_agent.scan(user_intent_input=user_intent_input)
        
        # Run Lambda Agent if Lambda resources are being scanned
        if 'lambda' in services_to_scan:
            lambda_agent = LambdaAgent(creds=self.creds)
            results["lambda"] = lambda_agent.analyze(user_intent_input=user_intent_input)
        
        # Default to S3 only if no specific service indicated
        if not services_to_scan or not results:
            s3_agent = S3Agent(creds=self.creds)
            results["s3"] = s3_agent.scan(user_intent_input=user_intent_input)
        
        return results
    
    def _determine_services(self, user_intent_input):
        """
        Determine which services to scan.
        If explicit service was provided, use only that.
        Otherwise, use heuristic detection based on resource names.
        
        Returns set of service names: {'s3', 'lambda', etc.}
        """
        # If explicit service was provided in __init__, use only that
        if self.service:
            return {self.service.lower()}
        
        if not user_intent_input:
            # If no input specified, scan both
            return {'s3', 'lambda'}
        
        services = set()
        
        # Check if any resource names look like Lambda functions
        # Lambda functions typically: contain underscores, hyphens, no dots
        # S3 buckets typically: contain dots, hyphens, lowercase only
        for resource_name in user_intent_input.keys():
            if resource_name == '_global_intent':
                # Global intent applies to all services
                return {'s3', 'lambda'}
            
            # Simple heuristics: if it looks like a function name, assume Lambda
            # This is best-effort; the agents will handle what they can
            if any(char in resource_name for char in ['_']):
                services.add('lambda')
            else:
                services.add('s3')
        
        # If no definitive service identified, scan both
        if not services:
            services = {'s3', 'lambda'}
        
        return services
