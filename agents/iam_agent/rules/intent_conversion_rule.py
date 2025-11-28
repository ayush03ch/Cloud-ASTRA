class IAMIntentConversion:
    id = "iam_intent_conversion"
    detection = "IAM config conflicts with stated user intent"
    auto_safe = False
    
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = False
        self.fix_type = None
        self.conflict_details = None
        
    def check_with_intent(self, entity_typ, entity_name, intent, recommendations):
        conflicts = []
        
        if intent == "least_privilage":
            attached_policies = client.list_attached_user_policies(UserName = entity_name) if entity_type == "user" \
                else client.list_attached_role_policies(RoleName = entity_name)
            for policy in attached_policies.get("AttachedPolicies", []):
                if "AdmistratorAccess" in policy['PolicyArn']:
                    conflicts.append({
                        "type" : "admin_policy_attached",
                        "current_config" : "AdmistratorAccess policy attached",
                        "user_intent" : intent,
                        "recommendation" : "Detach AdministratorAccess and attach only required policies"
                    })
                    
        if intent == "strong_security":
            mfa_devices = client.list_mfa_devices(UserName = entity_name)
            if not mfa_devices["MFADevices"]:
                conflicts.append({
                    "type": "mfa_missing",
                    "current_config": "No MFA device attached",
                    "user_intent": intent,
                    "recommendation": "Enable and require MFA for all IAM users"
                })
                
        if conflicts:
            self.conflict_details = conflicts
            self._set_conversion_instructions(conflicts[0])
            return True
        
        return False
    
    def _set_conversion_instructions(self, conflict):
        if conflict["type"] == "admin_policy_attached":
            self.fix_instructions = [
                f"Current: {conflict['current_config']}",
                f"User Intent: {conflict['user_intent']}",
                "",
                "🔧 Conversion Steps:",
                "1. Detach AdministratorAccess policy",
                "2. Attach only necessary permissions",
                "",
                "⚠️ Will restrict excessive permissions."
            ]
            
            self.can_auto_fix = True
            self.fix_type = "detach_admin_policy"
            
        elif conflict["type"] == "mfa_missing":
            self.fix_instructions = [
               f"Current: {conflict['current_config']}",
                f"User Intent: {conflict['user_intent']}",
                "",
                "🔧 Conversion Steps:",
                "1. Enroll user with MFA device",
                "2. Require MFA for console/login",
                "",
                "⚠️ User login will require MFA." 
            ]
            
            self.can_auto_fix = True
            self.fix_type = "enable_mfa"