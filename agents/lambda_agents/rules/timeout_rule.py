# agents/lambda_agents/rules/timeout_rule.py

class TimeoutRule:
    id = "lambda_timeout_excessive"
    detection = "Lambda function timeout is set too high or too low for its use case"
    auto_safe = True
    
    def __init__(self):
        self.fix_instructions = [
            "Set timeout based on expected execution time",
            "API endpoints: 30-60 seconds",
            "Batch processing: 300-900 seconds",
            "Scheduled tasks: depends on task complexity",
            "Monitor CloudWatch Metrics to find optimal timeout",
            "Avoid 15 minute (900s) max timeout unless necessary"
        ]
        self.can_auto_fix = True
        self.fix_type = "adjust_timeout"

    def check(self, client, function_name):
        """Check if timeout is appropriately configured."""
        try:
            config = client.get_function_configuration(FunctionName=function_name)
            timeout = config.get('Timeout', 3)  # Default is 3 seconds
            
            # Current heuristic: warn if timeout > 600 seconds (10 minutes)
            # This is conservative; adjust based on your use case
            if timeout > 600:
                print(f" Function {function_name} has excessive timeout: {timeout}s")
                return True
            
            # Also check for very low timeout (less than 5s) if it's likely an API
            if timeout < 5 and function_name.lower().endswith('api'):
                print(f" Function {function_name} might have insufficient timeout: {timeout}s")
                return True
            
            return False
        except Exception as e:
            print(f"Error checking timeout for {function_name}: {e}")
            return False

    def get_fix_action(self, function_name, suggested_timeout=30):
        """Get fix action for this rule."""
        return {
            "action": "adjust_timeout",
            "params": {
                "function_name": function_name,
                "timeout": suggested_timeout
            }
        }

    def fix(self, client, function_name, timeout=30):
        """Adjust Lambda function timeout."""
        print(f"⏱️  Adjusting timeout for function: {function_name}")
        
        client.update_function_configuration(
            FunctionName=function_name,
            Timeout=timeout
        )
        
        print(f" Successfully set timeout to {timeout}s for function: {function_name}")
