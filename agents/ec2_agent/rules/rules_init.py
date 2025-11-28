# agents/ec2_agent/rules/__init__.py

"""
EC2 Agent Rules Module
Contains detection and remediation rules for common EC2 misconfigurations
"""

from .ec2_open_security_group_rule import OpenSecurityGroupRule
from .ec2_unencrypted_ebs_rule import UnencryptedEBSRule
from .ec2_missing_backups_rule import MissingBackupsRule
from .intent_conversion_rule import EC2IntentConversionRule

# Export all rules
__all__ = [
    'OpenSecurityGroupRule',
    'UnencryptedEBSRule',
    'MissingBackupsRule', 
    'EC2IntentConversionRule'
]
