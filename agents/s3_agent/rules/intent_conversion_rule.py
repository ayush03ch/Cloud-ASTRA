# agents/s3_agent/rules/intent_conversion_rule.py

class IntentConversionRule:
    """
    Rule to handle intent conflicts - when user specifies one intent 
    but bucket is configured for another (e.g., user says 'data storage' 
    but bucket has website hosting enabled).
    """
    id = "s3_intent_conversion"
    detection = "Bucket configuration conflicts with user intent"
    auto_safe = False  # Always manual review for intent conflicts
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = True
        self.fix_type = None
        self.conflict_details = None

    def check_with_intent(self, client, bucket_name, intent, recommendations):
        """Check for intent vs configuration conflicts."""
        from agents.s3_agent.intent_detector import S3Intent
        
        conflicts = []
        
        # Check if user wants data storage but bucket has website hosting
        if intent in [S3Intent.DATA_STORAGE, S3Intent.DATA_ARCHIVAL, S3Intent.BACKUP_STORAGE, S3Intent.LOG_STORAGE]:
            try:
                website_config = client.get_bucket_website(Bucket=bucket_name)
                if website_config:
                    conflicts.append({
                        "type": "website_hosting_enabled",
                        "current_config": "Website hosting enabled",
                        "user_intent": intent.value,
                        "recommendation": "Disable website hosting and secure bucket"
                    })
                    print(f"⚠️ Intent conflict: User wants {intent.value} but bucket has website hosting enabled")
            except:
                pass  # No website config, no conflict
        
        # Check if user wants website hosting but bucket is private
        elif intent == S3Intent.WEBSITE_HOSTING:
            try:
                # Check if public access is blocked
                pab_config = client.get_public_access_block(Bucket=bucket_name)
                pab = pab_config.get('PublicAccessBlockConfiguration', {})
                
                if pab.get('BlockPublicPolicy', False) or pab.get('RestrictPublicBuckets', False):
                    conflicts.append({
                        "type": "public_access_blocked",
                        "current_config": "Public access blocked", 
                        "user_intent": intent.value,
                        "recommendation": "Enable public access for website hosting"
                    })
                    print(f"⚠️ Intent conflict: User wants website hosting but public access is blocked")
            except:
                pass
        
        if conflicts:
            self.conflict_details = conflicts
            self._set_conversion_instructions(conflicts[0])  # Use first conflict
            
            # DEBUG: Log what instructions were set
            print(f"🐛 DEBUG: IntentConversionRule set fix_instructions: {self.fix_instructions}")
            print(f"🐛 DEBUG: IntentConversionRule set can_auto_fix: {self.can_auto_fix}")
            print(f"🐛 DEBUG: IntentConversionRule set fix_type: {self.fix_type}")
            
            return True
            
        return False

    def _set_conversion_instructions(self, conflict):
        """Set specific instructions based on conflict type."""
        if conflict["type"] == "website_hosting_enabled":
            self.fix_instructions = [
                f"Current: {conflict['current_config']}",
                f"User Intent: {conflict['user_intent']}",
                "",
                "🔧 Conversion Steps:",
                "1. Disable static website hosting configuration",
                "2. Enable Public Access Block to prevent public access",
                "3. Remove any public bucket policies",
                "4. Set bucket ACL to private",
                "",
                "⚠️ This will make your bucket private and disable website access"
            ]
            self.can_auto_fix = True
            self.fix_type = "disable_website_hosting"
            
        elif conflict["type"] == "public_access_blocked":
            self.fix_instructions = [
                f"Current: {conflict['current_config']}",
                f"User Intent: {conflict['user_intent']}",
                "",
                "🔧 Conversion Steps:",
                "1. Configure Public Access Block for website hosting",
                "2. Add public read bucket policy for website objects",
                "3. Enable static website hosting if not already enabled",
                "4. Verify index and error documents are configured",
                "",
                "⚠️ This will make your bucket publicly accessible for website hosting"
            ]
            self.can_auto_fix = True
            self.fix_type = "enable_website_hosting"

    def check(self, client, bucket_name):
        """Legacy check method - not used."""
        return False

    def fix(self, client, bucket_name):
        """Fix method called by legacy fixer - delegates to executor."""
        print(f"🔄 Intent conversion fix should be handled by executor: {bucket_name}")
        return True