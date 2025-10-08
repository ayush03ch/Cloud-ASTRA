# agents/s3_agent/rules/website_hosting_rule.py

import json

class WebsiteHostingRule:
    """
    Intent-aware rule for S3 static website hosting.
    Only triggers when intent is WEBSITE_HOSTING and configuration is incomplete.
    """
    id = "s3_website_hosting"
    detection = "Static website hosting misconfiguration"
    auto_safe = False  # Default to manual, but can be auto for high confidence cases
    
    def __init__(self):
        self.fix_instructions = None
        self.can_auto_fix = True
        self.fix_type = None
        self.html_analysis = None
        self.intent_confidence = 0.0  # Store confidence for decision making

    def check(self, client, bucket_name):
        """
        Legacy check method - always returns False to avoid conflicts.
        Use check_with_intent instead.
        """
        return False

    def check_with_intent(self, client, bucket_name, intent, recommendations):
        """
        Intent-aware check - only applies to website hosting buckets.
        """
        from agents.s3_agent.intent_detector import S3Intent
        
        # Only check buckets with website hosting intent
        if intent != S3Intent.WEBSITE_HOSTING:
            return False
            
        print(f"🌐 Checking website hosting configuration for: {bucket_name}")
        
        # Check if website hosting is properly configured
        website_issues = []
        website_config = None
        
        # 1. Check if website hosting is enabled
        try:
            website_config = client.get_bucket_website(Bucket=bucket_name)
            index_document = website_config.get('IndexDocument', {}).get('Suffix', '')
            print(f"✅ Website hosting enabled with index: {index_document}")
        except Exception as e:
            if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'NoSuchWebsiteConfiguration':
                website_issues.append("website_hosting_not_enabled")
                print(f"❌ Website hosting not enabled")
            else:
                print(f"❌ Error checking website config: {e}")
                return False
        
        # 2. Analyze HTML files and index document mismatch
        html_analysis = self._analyze_html_files_detailed(client, bucket_name, website_config)
        
        if html_analysis["has_html_files"]:
            print(f"📄 Found HTML files: {html_analysis['html_files']}")
            
            # Check for index document mismatch
            if website_config and html_analysis["index_mismatch"]:
                website_issues.append("index_document_mismatch")
                print(f"⚠️ Index document mismatch: configured='{html_analysis['configured_index']}', found='{html_analysis['suggested_index']}'")
                
        else:
            # No HTML files found
            website_issues.append("no_html_files")
            print(f"❌ No HTML files found in bucket intended for website hosting")
            
        # 3. Check if objects are publicly accessible (only if has HTML files)
        if html_analysis["has_html_files"] and not self._are_objects_publicly_readable(client, bucket_name):
            website_issues.append("objects_not_public")
            print(f"❌ Objects not publicly readable")
            
        # Store detailed analysis for fixer
        if website_issues:
            # Store analysis in a way the fixer can access
            self._store_analysis(bucket_name, {
                "issues": website_issues,
                "html_analysis": html_analysis,
                "website_config": website_config
            })
            
            # Set fix instructions based on the specific issues found
            self._set_fix_instructions(website_issues, html_analysis)
            
            return True
            
        print(f"✅ Website hosting properly configured")
        return False

    def _set_fix_instructions(self, website_issues, html_analysis):
        """Set detailed fix instructions based on detected issues."""
        instructions = []
        
        if "no_html_files" in website_issues:
            instructions = [
                "Upload HTML files (index.html, etc.) to enable website hosting",
                "OR convert bucket to private data storage if website hosting not needed",
                "Agent can automatically convert to secure data storage"
            ]
            self.can_auto_fix = True
            self.fix_type = "disable_website_hosting"
            
        elif "index_document_mismatch" in website_issues:
            configured = html_analysis.get("configured_index", "")
            suggested = html_analysis.get("suggested_index", "")
            instructions = [
                f"❗ Index Document Mismatch Detected:",
                f"• Current config: '{configured}'",
                f"• Actual file found: '{suggested}'", 
                "",
                "🔧 Fix Options:",
                f"1. Update config to use '{suggested}' (recommended)",
                f"2. Rename '{suggested}' to '{configured}'",
                f"3. Upload new '{configured}' file",
                "",
                f"💡 Agent can automatically update config from '{configured}' to '{suggested}'"
            ]
            self.can_auto_fix = True
            self.fix_type = "index_document"
            
        elif "website_hosting_not_enabled" in website_issues and html_analysis["has_html_files"]:
            instructions = [
                "Enable static website hosting configuration",
                f"Set index document to: {html_analysis.get('suggested_index', 'index.html')}",
                "Configure public access for website hosting",
                "Agent can automatically enable website hosting"
            ]
            self.can_auto_fix = True
            self.fix_type = "enable_website_hosting"
            
        elif "objects_not_public" in website_issues:
            instructions = [
                "Enable public read access for website objects",
                "Configure bucket policy for public website access",
                "Disable Public Access Block for website hosting",
                "Agent can automatically configure public access"
            ]
            self.can_auto_fix = True
            self.fix_type = "enable_public_access"
        
        self.fix_instructions = instructions

    def _analyze_html_files_detailed(self, client, bucket_name, website_config):
        """Detailed analysis of HTML files and index document configuration."""
        try:
            response = client.list_objects_v2(Bucket=bucket_name, MaxKeys=100)
            objects = response.get('Contents', [])
            
            # Find all HTML files
            html_files = []
            for obj in objects:
                key = obj['Key'].lower()
                if key.endswith(('.html', '.htm')):
                    html_files.append(obj['Key'])  # Keep original case
            
            configured_index = website_config.get('IndexDocument', {}).get('Suffix', '') if website_config else ''
            
            # Determine suggested index file
            suggested_index = None
            index_mismatch = False
            
            if html_files:
                # Priority order for index files
                priority_names = ['index.html', 'index.htm', 'home.html', 'default.html', 'main.html']
                
                for priority_name in priority_names:
                    if any(f.lower() == priority_name for f in html_files):
                        suggested_index = next(f for f in html_files if f.lower() == priority_name)
                        break
                
                if not suggested_index:
                    suggested_index = html_files[0]  # Use first HTML file found
                
                # Check for mismatch
                if configured_index and configured_index.lower() != suggested_index.lower():
                    index_mismatch = True
                elif not configured_index:
                    index_mismatch = True  # No index configured but HTML files exist
            
            return {
                "has_html_files": bool(html_files),
                "html_files": html_files,
                "configured_index": configured_index,
                "suggested_index": suggested_index,
                "index_mismatch": index_mismatch
            }
            
        except Exception as e:
            print(f"❌ Error analyzing HTML files: {e}")
            return {
                "has_html_files": False,
                "html_files": [],
                "configured_index": "",
                "suggested_index": None,
                "index_mismatch": False
            }

    def _store_analysis(self, bucket_name, analysis):
        """Store analysis for the fixer to use."""
        # Simple storage - in production, use a proper cache/database
        if not hasattr(self, '_analysis_cache'):
            self._analysis_cache = {}
        self._analysis_cache[bucket_name] = analysis

    def _get_stored_analysis(self, bucket_name):
        """Retrieve stored analysis."""
        if hasattr(self, '_analysis_cache'):
            return self._analysis_cache.get(bucket_name, {})
        return {}

    def _is_website_hosting_enabled(self, client, bucket_name):
        """Check if static website hosting is enabled."""
        try:
            client.get_bucket_website(Bucket=bucket_name)
            return True
        except Exception as e:
            if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'NoSuchWebsiteConfiguration':
                return False
            return False

    def _are_objects_publicly_readable(self, client, bucket_name):
        """Check if objects can be publicly read."""
        try:
            response = client.get_bucket_policy(Bucket=bucket_name)
            policy = json.loads(response['Policy'])
            
            for statement in policy.get('Statement', []):
                if (statement.get('Effect') == 'Allow' and
                    statement.get('Principal') == '*' and
                    's3:GetObject' in statement.get('Action', [])):
                    return True
            return False
        except Exception as e:
            if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'NoSuchBucketPolicy':
                return False
            return False

    def _has_required_website_files(self, client, bucket_name):
        """Check if bucket has required website files."""
        try:
            response = client.list_objects_v2(Bucket=bucket_name, MaxKeys=100)
            objects = response.get('Contents', [])
            
            file_keys = [obj['Key'].lower() for obj in objects]
            
            # Check for index file
            has_index = any(key in ['index.html', 'index.htm'] for key in file_keys)
            
            return has_index
        except:
            return False

    def fix(self, client, bucket_name):
        """
        Fix website hosting configuration based on detected issues.
        """
        try:
            print(f"🔧 Analyzing website hosting issues for: {bucket_name}")
            
            # Get stored analysis from check phase
            analysis = self._get_stored_analysis(bucket_name)
            issues = analysis.get("issues", [])
            html_analysis = analysis.get("html_analysis", {})
            
            if not issues:
                print(f"ℹ️ No specific issues found, applying standard website hosting fix")
                self._apply_standard_website_fix(client, bucket_name)
                return
            
            # Handle different issue types - order matters!
            issues_handled = []
            
            if "no_html_files" in issues:
                self._handle_no_html_files(client, bucket_name)
                issues_handled.append("no_html_files")
            
            # Enable website hosting first if needed
            if "website_hosting_not_enabled" in issues:
                self._handle_website_hosting_disabled(client, bucket_name, html_analysis)
                issues_handled.append("website_hosting_not_enabled")
            
            # Then fix index document mismatch (this might override the previous index setting)
            if "index_document_mismatch" in issues:
                self._handle_index_mismatch(client, bucket_name, html_analysis)
                issues_handled.append("index_document_mismatch")
            
            # Finally ensure public access is set correctly
            if "objects_not_public" in issues:
                self._handle_objects_not_public(client, bucket_name)
                issues_handled.append("objects_not_public")
            
            if not issues_handled:
                print(f"ℹ️ No specific issue handlers found, applying standard website hosting fix")
                self._apply_standard_website_fix(client, bucket_name)
            else:
                print(f"✅ Handled issues: {issues_handled}")
                
        except Exception as e:
            print(f"❌ Error fixing website hosting: {e}")
            raise

    def _handle_no_html_files(self, client, bucket_name):
        """Handle case where bucket is intended for website but has no HTML files."""
        print(f"🤔 No HTML files found in bucket '{bucket_name}' intended for website hosting")
        print(f"")
        print(f"� RECOMMENDED ACTIONS:")
        print(f"1. 📄 Upload HTML files (index.html, etc.) if this should be a website")
        print(f"2. 🔒 Convert to private data storage if website hosting not needed")
        print(f"")
        print(f"⚠️ AUTO-FIX: Converting bucket to secure data storage (no website hosting)")
        
        # Convert to data storage bucket
        try:
            # Remove website configuration
            client.delete_bucket_website(Bucket=bucket_name)
            print(f"✅ Removed website hosting configuration")
        except Exception as e:
            if "NoSuchWebsiteConfiguration" not in str(e):
                print(f"⚠️ Could not remove website config: {e}")
        
        # Apply data storage security
        self._apply_data_storage_security(client, bucket_name)

    def _handle_index_mismatch(self, client, bucket_name, html_analysis):
        """Handle index document mismatch."""
        configured = html_analysis.get("configured_index", "")
        suggested = html_analysis.get("suggested_index", "")
        
        print(f"🔧 FIXING INDEX DOCUMENT MISMATCH:")
        print(f"   Currently configured: '{configured}'")
        print(f"   Suggested fix: '{suggested}'")
        print(f"")
        
        if suggested:
            # Update index document to match available file
            client.put_bucket_website(
                Bucket=bucket_name,
                WebsiteConfiguration={
                    'IndexDocument': {'Suffix': suggested},
                    'ErrorDocument': {'Key': 'error.html'}
                }
            )
            print(f"✅ Updated index document to: {suggested}")
        
        # Also ensure public access
        self._apply_website_public_access(client, bucket_name)

    def _handle_website_hosting_disabled(self, client, bucket_name, html_analysis):
        """Handle case where website hosting is disabled but HTML files exist."""
        suggested_index = html_analysis.get("suggested_index", "index.html")
        
        print(f"🌐 Enabling website hosting with index: {suggested_index}")
        
        client.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                'IndexDocument': {'Suffix': suggested_index},
                'ErrorDocument': {'Key': 'error.html'}
            }
        )
        print(f"✅ Enabled website hosting with index: {suggested_index}")
        
        # Apply public access for website
        self._apply_website_public_access(client, bucket_name)

    def _handle_objects_not_public(self, client, bucket_name):
        """Handle case where objects are not publicly readable."""
        print(f"🔓 Making objects publicly readable for website hosting")
        self._apply_website_public_access(client, bucket_name)

    def _apply_standard_website_fix(self, client, bucket_name):
        """Apply standard website hosting configuration."""
        print(f"🌐 Applying standard website hosting configuration")
        
        # Detect the best index file to use
        html_analysis = self._analyze_html_files_detailed(client, bucket_name, None)
        index_file = html_analysis.get("suggested_index", "index.html")
        
        print(f"🔍 Detected index file: {index_file}")
        
        # Enable website hosting
        client.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                'IndexDocument': {'Suffix': index_file},
                'ErrorDocument': {'Key': 'error.html'}
            }
        )
        print(f"✅ Enabled website hosting with index: {index_file}")
        
        # Apply public access
        self._apply_website_public_access(client, bucket_name)

    def _apply_website_public_access(self, client, bucket_name):
        """Apply public access configuration for website hosting."""
        import json
        
        # Step 1: Configure Public Access Block for website
        client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,        # Block public ACLs (good security)
                'IgnorePublicAcls': True,       # Ignore public ACLs (good security)
                'BlockPublicPolicy': False,     # Allow public policy (needed for website)
                'RestrictPublicBuckets': False  # Allow this specific public policy
            }
        )
        print(f"✅ Configured Public Access Block for website hosting")
        
        # Step 2: Apply public read policy
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(policy)
        )
        print(f"✅ Applied public read policy")

    def _apply_data_storage_security(self, client, bucket_name):
        """Apply security configuration for data storage bucket."""
        print(f"🔒 Applying data storage security configuration")
        
        # Block all public access
        client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }
        )
        print(f"✅ Blocked all public access")
        
        # Remove any public bucket policy
        try:
            client.delete_bucket_policy(Bucket=bucket_name)
            print(f"✅ Removed public bucket policy")
        except Exception as e:
            if "NoSuchBucketPolicy" not in str(e):
                print(f"⚠️ Could not remove bucket policy: {e}")
        
        print(f"🔒 Bucket '{bucket_name}' is now configured for secure data storage")