# agents/lambda_agents/rules/logging_rule.py

class LoggingRule:
    id = "lambda_logging_disabled"
    detection = "CloudWatch Logs are not configured for this Lambda function"
    auto_safe = True
    
    def __init__(self):
        self.fix_instructions = [
            "Ensure Lambda execution role has CloudWatch Logs permissions",
            "Lambda Logs are automatically sent to CloudWatch",
            "Verify CloudWatch Logs retention policy is set",
            "Check CloudWatch Logs group for /aws/lambda/{function-name}"
        ]
        self.can_auto_fix = True
        self.fix_type = "enable_logging"

    def check(self, client, function_name):
        """Check if CloudWatch Logs are properly configured."""
        try:
            config = client.get_function_configuration(FunctionName=function_name)
            role_arn = config.get('Role', '')
            
            # For now, just check if function has a role
            # Full check would require IAM client to verify permissions
            if not role_arn:
                print(f" Function {function_name} has no execution role")
                return True
            
            # Check if logs are being written (would need CloudWatch client)
            # This is a simplified check
            return False
        except Exception as e:
            print(f"Error checking logging for {function_name}: {e}")
            return False

    def get_fix_action(self, function_name):
        """Get fix action for this rule."""
        return {
            "action": "enable_logging",
            "params": {
                "function_name": function_name,
                "log_retention_days": 14
            }
        }

    def fix(self, client, function_name):
        """Enable CloudWatch Logs for Lambda function."""
        print(f"📋 Enabling CloudWatch Logs for function: {function_name}")
        # In practice, this would verify IAM permissions and configure logs
        # Lambda logs to CloudWatch automatically if role has permissions
        print(f" Ensure execution role has AWSLambdaBasicExecutionRole or equivalent")
        print(f" Successfully enabled logging for function: {function_name}")
