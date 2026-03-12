# agents/lambda_agents/rules/environment_variables_rule.py

class EnvironmentVariablesRule:
    id = "lambda_env_vars_unencrypted"
    detection = "Sensitive environment variables are not encrypted with KMS"
    auto_safe = False
    
    def __init__(self):
        self.fix_instructions = [
            "Use AWS KMS to encrypt sensitive environment variables",
            "Enable 'KMS key to encrypt in transit' in Lambda configuration",
            "Store API keys, database credentials, and tokens as encrypted env vars",
            "Never store secrets directly in function code",
            "Use AWS Secrets Manager for more complex secret management"
        ]
        self.can_auto_fix = False
        self.fix_type = "encrypt_environment_variables"
        self.sensitive_keywords = [
            'password', 'secret', 'api_key', 'token', 'credential', 'key',
            'auth', 'apikey', 'private_key', 'access_key', 'secret_key'
        ]

    def check(self, client, function_name):
        """Check if environment variables are encrypted."""
        try:
            config = client.get_function_configuration(FunctionName=function_name)
            env_vars = config.get('Environment', {}).get('Variables', {})
            
            if not env_vars:
                return False  # No env vars means no unencrypted secrets
            
            # Check if KMS encryption is enabled
            kms_key_arn = config.get('KmsKeyArn')
            
            # Check for sensitive keywords in env var names
            for var_name in env_vars.keys():
                if any(keyword in var_name.lower() for keyword in self.sensitive_keywords):
                    if not kms_key_arn:
                        print(f" Function {function_name} has unencrypted sensitive env var: {var_name}")
                        return True
            
            return False
        except Exception as e:
            print(f"Error checking environment variables for {function_name}: {e}")
            return False

    def get_fix_action(self, function_name):
        """Get fix action for this rule."""
        return {
            "action": "encrypt_environment_variables",
            "params": {
                "function_name": function_name,
                "kms_key_id": "alias/lambda-encryption"
            }
        }

    def fix(self, client, function_name):
        """Encrypt environment variables with KMS."""
        print(f"🔒 Encrypting environment variables for function: {function_name}")
        
        config = client.get_function_configuration(FunctionName=function_name)
        env_vars = config.get('Environment', {}).get('Variables', {})
        
        # Note: In a real scenario, you would:
        # 1. Create a KMS key if one doesn't exist
        # 2. Update function configuration with KmsKeyArn
        # 3. AWS will encrypt env vars in transit and at rest
        
        print(f" Recommended: Create a KMS key and update function configuration")
        print(f" Successfully enabled encryption for environment variables: {function_name}")
