# agents/iam_agent/rules/__init__.py

"""
IAM Agent Rules Module
Contains detection and remediation rules for common IAM misconfigurations
"""

from .mfa_enforcement_rule import MFAEnforcementRule
from .least_privilege_rule import LeastPrivilegeRule
from .access_key_rotation_rule import AccessKeyRotationRule
from .inactive_user_rule import InactiveUserRule
from .intent_conversion_rule import IAMIntentConversionRule

# Export all rules
__all__ = [
    'MFAEnforcementRule',
    'LeastPrivilegeRule', 
    'AccessKeyRotationRule',
    'InactiveUserRule',
    'IAMIntentConversionRule'
]

# Rule registry for dynamic loading
RULE_REGISTRY = {
    'mfa_enforcement': MFAEnforcementRule,
    'least_privilege': LeastPrivilegeRule,
    'access_key_rotation': AccessKeyRotationRule,
    'inactive_user': InactiveUserRule,
    'intent_conversion': IAMIntentConversionRule
}

# Rule categories for organization
RULE_CATEGORIES = {
    'security': [
        'mfa_enforcement',
        'least_privilege',
        'access_key_rotation'
    ],
    'compliance': [
        'least_privilege',
        'mfa_enforcement',
        'inactive_user',
        'access_key_rotation'
    ],
    'operational': [
        'inactive_user',
        'access_key_rotation'
    ],
    'intent_based': [
        'intent_conversion'
    ]
}

# Rule priorities (higher number = higher priority)
RULE_PRIORITIES = {
    'mfa_enforcement': 8,
    'least_privilege': 9,  # Highest priority
    'access_key_rotation': 6,
    'inactive_user': 5,
    'intent_conversion': 7
}

def get_rule_by_name(rule_name):
    """Get rule class by name."""
    return RULE_REGISTRY.get(rule_name)

def get_rules_by_category(category):
    """Get all rules in a category."""
    rule_names = RULE_CATEGORIES.get(category, [])
    return [RULE_REGISTRY[name] for name in rule_names if name in RULE_REGISTRY]

def get_all_rules():
    """Get all available rule classes."""
    return list(RULE_REGISTRY.values())

def get_rule_info():
    """Get information about all rules."""
    rules_info = {}
    
    for rule_name, rule_class in RULE_REGISTRY.items():
        # Create instance to get rule details
        instance = rule_class()
        
        rules_info[rule_name] = {
            'class': rule_class,
            'id': getattr(instance, 'id', rule_name),
            'detection': getattr(instance, 'detection', 'No description available'),
            'auto_safe': getattr(instance, 'auto_safe', False),
            'priority': RULE_PRIORITIES.get(rule_name, 5),
            'categories': [cat for cat, rules in RULE_CATEGORIES.items() if rule_name in rules]
        }
    
    return rules_info

# Common rule execution helpers
class RuleExecutor:
    """Helper class for executing rules systematically."""
    
    def __init__(self, client):
        self.client = client
        self.executed_rules = {}
        self.rule_results = {}
    
    def execute_rule(self, rule_name, *args, **kwargs):
        """Execute a single rule by name."""
        rule_class = get_rule_by_name(rule_name)
        
        if not rule_class:
            return {"error": f"Rule '{rule_name}' not found"}
        
        try:
            rule_instance = rule_class()
            result = rule_instance.check(self.client, *args, **kwargs)
            
            self.executed_rules[rule_name] = rule_instance
            self.rule_results[rule_name] = {
                'detected': result,
                'can_auto_fix': getattr(rule_instance, 'can_auto_fix', False),
                'fix_type': getattr(rule_instance, 'fix_type', None),
                'fix_instructions': getattr(rule_instance, 'fix_instructions', None)
            }
            
            return self.rule_results[rule_name]
            
        except Exception as e:
            error_result = {"error": f"Error executing rule '{rule_name}': {str(e)}"}
            self.rule_results[rule_name] = error_result
            return error_result
    
    def execute_category(self, category, *args, **kwargs):
        """Execute all rules in a category."""
        rules = get_rules_by_category(category)
        results = {}
        
        for rule_class in rules:
            rule_name = None
            # Find rule name from registry
            for name, cls in RULE_REGISTRY.items():
                if cls == rule_class:
                    rule_name = name
                    break
            
            if rule_name:
                results[rule_name] = self.execute_rule(rule_name, *args, **kwargs)
        
        return results
    
    def execute_all_rules(self, *args, **kwargs):
        """Execute all available rules."""
        results = {}
        
        for rule_name in RULE_REGISTRY.keys():
            results[rule_name] = self.execute_rule(rule_name, *args, **kwargs)
        
        return results
    
    def get_fixable_issues(self):
        """Get all issues that can be auto-fixed."""
        fixable = {}
        
        for rule_name, result in self.rule_results.items():
            if result.get('detected') and result.get('can_auto_fix'):
                fixable[rule_name] = {
                    'rule_instance': self.executed_rules.get(rule_name),
                    'fix_type': result.get('fix_type'),
                    'auto_safe': getattr(self.executed_rules.get(rule_name), 'auto_safe', False)
                }
        
        return fixable
    
    def apply_fixes(self, rule_names=None, auto_approve=False):
        """Apply fixes for specified rules or all fixable rules."""
        if rule_names is None:
            fixable = self.get_fixable_issues()
            rule_names = list(fixable.keys())
        
        fix_results = {}
        
        for rule_name in rule_names:
            if rule_name in self.executed_rules:
                rule_instance = self.executed_rules[rule_name]
                
                try:
                    if hasattr(rule_instance, 'fix'):
                        # Different rules have different fix signatures
                        # Try to call fix method appropriately
                        fix_result = self._call_fix_method(rule_instance, auto_approve)
                        fix_results[rule_name] = fix_result
                    else:
                        fix_results[rule_name] = {
                            "success": False,
                            "message": f"Rule {rule_name} does not implement fix method"
                        }
                        
                except Exception as e:
                    fix_results[rule_name] = {
                        "success": False,
                        "message": f"Error applying fix for {rule_name}: {str(e)}"
                    }
        
        return fix_results
    
    def _call_fix_method(self, rule_instance, auto_approve):
        """Call the fix method with appropriate parameters."""
        try:
            # Try different fix method signatures
            if hasattr(rule_instance, 'old_keys'):
                # Access key rotation rule
                return rule_instance.fix(self.client, auto_approve=auto_approve)
            elif hasattr(rule_instance, 'inactive_users'):
                # Inactive user rule
                return rule_instance.fix(self.client, fix_option="disable", auto_approve=auto_approve)
            elif hasattr(rule_instance, 'privilege_violations'):
                # Least privilege rule - needs entity info
                return {"success": False, "message": "Requires entity type and name parameters"}
            else:
                # Generic fix method
                return rule_instance.fix(self.client, auto_approve=auto_approve)
                
        except TypeError:
            # If method signature doesn't match, try basic call
            return rule_instance.fix(self.client)