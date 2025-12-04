# agents/lambda_agents/rules/memory_rule.py

class MemoryRule:
    id = "lambda_memory_low"
    detection = "Lambda function memory allocation may be insufficient for its workload"
    auto_safe = True
    
    def __init__(self):
        self.fix_instructions = [
            "Allocate memory based on workload requirements",
            "API handlers: 256-512 MB",
            "Data processing: 512-1024 MB",
            "Heavy computation: 1024-3008 MB",
            "Check CloudWatch Metrics for memory usage patterns",
            "More memory = higher CPU speed = faster execution",
            "More memory also increases cost, so optimize accordingly"
        ]
        self.can_auto_fix = True
        self.fix_type = "adjust_memory"

    def check(self, client, function_name):
        """Check if memory allocation is appropriate."""
        try:
            config = client.get_function_configuration(FunctionName=function_name)
            memory = config.get('MemorySize', 128)  # Default is 128 MB
            
            # Check for very low memory (less than 128 MB is now minimum)
            # AWS Lambda now requires minimum 128 MB
            if memory < 128:
                print(f" Function {function_name} has insufficient memory: {memory}MB")
                return True
            
            # Warn if memory is too low for potential workloads
            # This is a heuristic based on function name or description
            description = config.get('Description', '').lower()
            function_name_lower = function_name.lower()
            
            is_data_processing = any(kw in function_name_lower + description for kw in 
                                    ['process', 'transform', 'etl', 'analytics', 'data'])
            is_api = any(kw in function_name_lower + description for kw in 
                        ['api', 'rest', 'http', 'handler', 'endpoint'])
            
            if is_data_processing and memory < 512:
                print(f" Function {function_name} might need more memory for processing: {memory}MB")
                return True
            
            if is_api and memory < 256:
                print(f" Function {function_name} might need more memory for API: {memory}MB")
                return True
            
            return False
        except Exception as e:
            print(f"Error checking memory for {function_name}: {e}")
            return False

    def get_fix_action(self, function_name, suggested_memory=256):
        """Get fix action for this rule."""
        return {
            "action": "adjust_memory",
            "params": {
                "function_name": function_name,
                "memory": suggested_memory
            }
        }

    def fix(self, client, function_name, memory=256):
        """Adjust Lambda function memory allocation."""
        print(f"💾 Adjusting memory for function: {function_name}")
        
        # Validate memory is in valid range (128 - 10240 MB in 1MB increments)
        if memory < 128:
            memory = 128
        elif memory > 10240:
            memory = 10240
        
        client.update_function_configuration(
            FunctionName=function_name,
            MemorySize=memory
        )
        
        print(f" Successfully set memory to {memory}MB for function: {function_name}")
