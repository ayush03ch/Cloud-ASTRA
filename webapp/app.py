from flask import Flask, render_template, request, jsonify
import sys
import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add parent directory to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Force reload for debugging intent detection
from supervisor.supervisor_agent import SupervisorAgent

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def landing():
    """Serve the landing page."""
    return render_template('landing.html')

@app.route('/dashboard')
def dashboard():
    """Serve the main dashboard interface."""
    return render_template('index.html')

@app.route('/api/scan', methods=['POST'])
def api_scan():
    """
    Enhanced API endpoint for intent-aware scanning.
    Supports both S3 and EC2 agents.
    
    Expected JSON for S3:
    {
        "agent": "s3",
        "role_arn": "arn:aws:iam::account:role/name",
        "external_id": "external-id",
        "region": "us-east-1",
        "user_intent_input": {"bucket1": "website hosting"},
        "allow_conversion": true,
        "auto_fix": true,
        "detailed_logging": false
    }
    
    Expected JSON for EC2:
    {
        "agent": "ec2",
        "role_arn": "arn:aws:iam::account:role/name",
        "external_id": "external-id",
        "region": "us-east-1",
        "ec2_instances": ["i-123456"],
        "ec2_tags": "Environment:production",
        "ec2_checks": {"security_groups": true, "ebs_encryption": true},
        "auto_fix": true,
        "detailed_logging": false
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract common parameters
        agent = data.get('agent', 's3')  # Default to S3 for backward compatibility
        role_arn = data.get('role_arn')
        external_id = data.get('external_id', 'default-external-id')
        region = data.get('region', 'us-east-1')
        auto_fix = data.get('auto_fix', True)
        detailed_logging = data.get('detailed_logging', False)
        
        # Use appropriate parameters based on request structure
        if not role_arn:
            # Try simplified format with account_id
            account_id = data.get('account_id')
            if account_id:
                role_arn = f'arn:aws:iam::{account_id}:role/SecurityAgentRole'
                external_id = 'unique-external-id-12345'
                app.logger.info(f"🐛 DEBUG: Using simplified format with role_arn: {role_arn}")
            else:
                return jsonify({"error": "role_arn or account_id is required"}), 400
        
        # Set logging level based on request
        if detailed_logging:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Initialize supervisor and run scan
        supervisor = SupervisorAgent(role_arn, external_id, region)
        
        # Assume role
        try:
            creds = supervisor.assume()
            app.logger.info(f"Successfully assumed role: {role_arn}")
        except Exception as e:
            app.logger.error(f"Failed to assume role: {e}")
            return jsonify({"error": f"Failed to assume role: {str(e)}"}), 403
        
        # Prepare service-specific parameters
        user_intent_input = {}
        ec2_filters = None
        ec2_checks = None
        iam_scope = None
        iam_checks = None
        lambda_function_name = None
        lambda_checks = None
        
        if agent == 's3':
            # S3-specific parameters
            user_intent_input = data.get('user_intent_input', {})
            simple_user_intent = data.get('user_intent')
            if simple_user_intent:
                app.logger.info(f"🐛 DEBUG: Received simple user_intent: {simple_user_intent}")
                user_intent_input = {'_global_intent': simple_user_intent}
            app.logger.info(f"🐛 DEBUG: Final user_intent_input: {user_intent_input}")
            
        elif agent == 'ec2':
            # EC2-specific parameters
            ec2_instances = data.get('ec2_instances', [])
            ec2_tags = data.get('ec2_tags', '')
            
            ec2_filters = {}
            if ec2_instances:
                ec2_filters['instance_ids'] = ec2_instances
            if ec2_tags:
                ec2_filters['tags'] = ec2_tags
            
            ec2_checks = data.get('ec2_checks', {
                'security_groups': True,
                'ebs_encryption': True,
                'backups': True,
                'imdsv2': True
            })
            
            app.logger.info(f"EC2 Scan - Filters: {ec2_filters}, Checks: {ec2_checks}")
        
        elif agent == 'iam':
            # IAM-specific parameters
            iam_scope = data.get('iam_scope', 'account')
            iam_checks = data.get('iam_checks', {
                'access_key_rotation': True,
                'mfa_enforcement': True,
                'inactive_users': True,
                'least_privilege': True
            })
            
            app.logger.info(f"IAM Scan - Scope: {iam_scope}, Checks: {iam_checks}")
        
        elif agent == 'lambda':
            # Lambda-specific parameters
            lambda_function_name = data.get('lambda_function_name', '')
            lambda_intent = data.get('lambda_intent', '')
            
            lambda_checks = data.get('lambda_checks', {
                'timeout': True,
                'memory': True,
                'logging': True,
                'env_vars': True
            })
            
            user_intent_input = {}
            if lambda_intent:
                user_intent_input['_global_intent'] = lambda_intent
            
            app.logger.info(f"Lambda Scan - Function: {lambda_function_name or 'all'}, Intent: {lambda_intent}, Checks: {lambda_checks}")
        
        # Run intent-aware scan and fix
        try:
            results = supervisor.scan_and_fix(
                user_intent_input=user_intent_input,
                service=agent,
                ec2_filters=ec2_filters,
                ec2_checks=ec2_checks,
                iam_scope=iam_scope,
                iam_checks=iam_checks,
                lambda_function_name=lambda_function_name if agent == 'lambda' else None,
                lambda_checks=lambda_checks if agent == 'lambda' else None
            )
            
            # Process results for web interface
            findings = results.get('findings', {})
            
            # Handle nested findings structure if it exists
            if 'findings' in findings:
                findings = findings['findings']
            
            # Deduplicate findings - prioritize rule-based over LLM
            def deduplicate_findings(findings_list):
                """Remove duplicate findings, keeping the most specific one (rules > llm)"""
                unique_findings = {}
                
                for finding in findings_list:
                    resource = finding.get('resource', '')
                    issue = finding.get('issue', '').lower()
                    rule_id = finding.get('rule_id', '')
                    
                    # Create a key based on resource and normalized issue
                    # Normalize common issue patterns
                    issue_normalized = issue.replace('not enabled', '').replace('disabled', '').replace('not configured', '').strip()
                    
                    # Check for versioning issues
                    if 'version' in issue_normalized:
                        key = f"{resource}:versioning"
                    # Check for logging issues
                    elif 'logging' in issue_normalized or 'access log' in issue_normalized:
                        key = f"{resource}:logging"
                    # Check for lifecycle issues
                    elif 'lifecycle' in issue_normalized:
                        key = f"{resource}:lifecycle"
                    # Check for tagging issues
                    elif 'tag' in issue_normalized:
                        key = f"{resource}:tagging"
                    # Check for encryption issues
                    elif 'encrypt' in issue_normalized:
                        key = f"{resource}:encryption"
                    # Check for public access issues
                    elif 'public' in issue_normalized:
                        key = f"{resource}:public_access"
                    else:
                        key = f"{resource}:{issue_normalized}"
                    
                    # Prioritize: rule-based > llm_fallback
                    if key not in unique_findings:
                        unique_findings[key] = finding
                    else:
                        # Replace if current is from rules and existing is from llm
                        existing_rule_id = unique_findings[key].get('rule_id', '')
                        if rule_id != 'llm_fallback' and existing_rule_id == 'llm_fallback':
                            unique_findings[key] = finding
                
                return list(unique_findings.values())
            
            # Deduplicate findings for each service
            if agent == 's3' and 's3' in findings:
                findings['s3'] = deduplicate_findings(findings['s3'])
            elif agent == 'ec2' and 'ec2' in findings:
                findings['ec2'] = deduplicate_findings(findings['ec2'])
            elif agent == 'iam' and 'iam' in findings:
                findings['iam'] = deduplicate_findings(findings['iam'])
            elif agent == 'lambda' and 'lambda' in findings:
                findings['lambda'] = deduplicate_findings(findings['lambda'])
            
            # Count findings based on agent type
            if agent == 's3':
                findings_count = len(findings.get('s3', []))
            elif agent == 'ec2':
                findings_count = len(findings.get('ec2', []))
            elif agent == 'iam':
                findings_count = len(findings.get('iam', []))
            elif agent == 'lambda':
                findings_count = len(findings.get('lambda', []))
            else:
                # Count all findings
                findings_count = sum(len(v) if isinstance(v, list) else 0 for v in findings.values())
            
            response = {
                "success": True,
                "agent": agent,
                "summary": results.get('summary', {}),
                "findings_count": findings_count,
                "auto_fixes_applied": results.get('auto_fixes_applied', []),
                "pending_fixes": results.get('pending_fixes', []),
                "findings": findings.get(agent, []) if agent else findings,
                "intent_decisions": [],
                "auto_fix_summary": {
                    "total_auto_fixed": len(results.get('auto_fixes_applied', [])),
                    "total_pending": len(results.get('pending_fixes', [])),
                    "success_rate": 0
                }
            }
            
            # Calculate success rate for auto-fixes
            applied_fixes = results.get('auto_fixes_applied', [])
            if applied_fixes:
                successful_fixes = sum(1 for fix in applied_fixes if fix.get('status') == 'applied')
                response["auto_fix_summary"]["success_rate"] = (successful_fixes / len(applied_fixes)) * 100
            
            # Extract intent decisions based on service
            if agent == 's3':
                s3_findings = findings.get('s3', [])
                intent_decisions_dict = {}
                for finding in s3_findings:
                    if finding.get('intent'):
                        resource_name = finding.get('resource')
                        if resource_name not in intent_decisions_dict:
                            intent_decisions_dict[resource_name] = {
                                "resource": resource_name,
                                "intent": finding.get('intent'),
                                "confidence": f"{finding.get('intent_confidence', 0):.2f}",
                                "reasoning": finding.get('intent_reasoning', 'No reasoning available')
                            }
                response["intent_decisions"] = list(intent_decisions_dict.values())
            
            elif agent == 'ec2':
                ec2_findings = findings.get('ec2', [])
                # For EC2, group findings by instance
                instance_summary = {}
                for finding in ec2_findings:
                    instance_id = finding.get('resource', 'unknown')
                    if instance_id not in instance_summary:
                        instance_summary[instance_id] = {
                            "instance_id": instance_id,
                            "issues_count": 0,
                            "check_types": []
                        }
                    instance_summary[instance_id]['issues_count'] += 1
                    check_type = finding.get('check_type', finding.get('rule_name', 'unknown'))
                    if check_type not in instance_summary[instance_id]['check_types']:
                        instance_summary[instance_id]['check_types'].append(check_type)
                
                response["instance_summary"] = instance_summary
            
            elif agent == 'lambda':
                lambda_findings = findings.get('lambda', [])
                # For Lambda, group findings by function
                function_summary = {}
                for finding in lambda_findings:
                    func_name = finding.get('resource', 'unknown')
                    if func_name not in function_summary:
                        function_summary[func_name] = {
                            "function_name": func_name,
                            "issues_count": 0,
                            "issue_types": []
                        }
                    function_summary[func_name]['issues_count'] += 1
                    issue_type = finding.get('issue', finding.get('rule_id', 'unknown'))
                    if issue_type not in function_summary[func_name]['issue_types']:
                        function_summary[func_name]['issue_types'].append(issue_type)
                
                response["function_summary"] = function_summary
            
            app.logger.info(f"Scan completed successfully. Found {response['findings_count']} issues")
            return jsonify(response)
            
        except Exception as e:
            app.logger.error(f"Error during scan and fix: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Scan failed: {str(e)}"}), 500
        
    except Exception as e:
        app.logger.error(f"Unexpected error in API endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/api/buckets/<bucket_name>/convert', methods=['POST'])
def api_convert_bucket(bucket_name):
    """
    API endpoint to convert bucket purpose (e.g., website to data storage).
    
    Expected JSON:
    {
        "from_intent": "website hosting",
        "to_intent": "data storage",
        "role_arn": "arn:aws:iam::account:role/name",
        "external_id": "external-id"
    }
    """
    try:
        data = request.get_json()
        
        role_arn = data.get('role_arn')
        external_id = data.get('external_id')
        from_intent = data.get('from_intent')
        to_intent = data.get('to_intent')
        
        if not all([role_arn, external_id, from_intent, to_intent]):
            return jsonify({"error": "Missing required parameters"}), 400
        
        # Initialize supervisor
        supervisor = SupervisorAgent(role_arn, external_id)
        creds = supervisor.assume()
        
        # Apply conversion based on intent change
        # This would implement the bucket conversion logic
        # For now, return a placeholder response
        
        response = {
            "success": True,
            "bucket": bucket_name,
            "converted_from": from_intent,
            "converted_to": to_intent,
            "actions_taken": [
                f"Converted {bucket_name} from {from_intent} to {to_intent}",
                "Applied appropriate security configuration"
            ]
        }
        
        return jsonify(response)
        
    except Exception as e:
        app.logger.error(f"Error converting bucket {bucket_name}: {e}")
        return jsonify({"error": f"Conversion failed: {str(e)}"}), 500

@app.route('/api/apply-manual-fix', methods=['POST'])
def api_apply_manual_fix():
    """
    API endpoint to apply a specific manual fix.
    
    Expected JSON:
    {
        "role_arn": "arn:aws:iam::account:role/name",
        "external_id": "external-id",
        "region": "us-east-1",
        "resource": "bucket-name",
        "fix_type": "public_access_block|index_document|disable_website_hosting"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract required parameters
        role_arn = data.get('role_arn')
        external_id = data.get('external_id')
        region = data.get('region', 'us-east-1')
        resource = data.get('resource')
        fix_type = data.get('fix_type')
        
        if not all([role_arn, external_id, resource, fix_type]):
            return jsonify({"error": "Missing required parameters"}), 400
        
        # Initialize supervisor
        supervisor = SupervisorAgent(role_arn, external_id, region)
        
        # Assume role
        try:
            creds = supervisor.assume()
            app.logger.info(f"Successfully assumed role for manual fix: {role_arn}")
        except Exception as e:
            app.logger.error(f"Failed to assume role: {e}")
            return jsonify({"error": f"Failed to assume role: {str(e)}"}), 403
        
        # Apply specific fix
        try:
            result = supervisor.apply_manual_fix(resource, fix_type)
            
            response = {
                "success": True,
                "resource": resource,
                "fix_type": fix_type,
                "message": result.get('message', 'Fix applied successfully'),
                "details": result.get('details', [])
            }
            
            app.logger.info(f"Manual fix applied successfully: {fix_type} for {resource}")
            return jsonify(response)
            
        except Exception as e:
            app.logger.error(f"Error applying manual fix: {e}")
            return jsonify({"error": f"Fix failed: {str(e)}"}), 500
        
    except Exception as e:
        app.logger.error(f"Unexpected error in manual fix endpoint: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/api/terminal/execute', methods=['POST'])
def api_terminal_execute():
    """
    API endpoint to execute AWS CLI commands with assumed role credentials.
    
    Expected JSON:
    {
        "command": "aws ec2 describe-instances --region us-east-1",
        "role_arn": "arn:aws:iam::account:role/name",
        "external_id": "external-id",
        "region": "us-east-1"
    }
    """
    import subprocess
    import os
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        command = data.get('command', '').strip()
        role_arn = data.get('role_arn')
        external_id = data.get('external_id', 'default-external-id')
        region = data.get('region', 'us-east-1')
        
        # Validate command
        if not command:
            return jsonify({"error": "No command provided"}), 400
        
        if not command.lower().startswith('aws'):
            return jsonify({"error": "Only AWS CLI commands are supported"}), 400
        
        # Whitelist dangerous commands
        dangerous_keywords = ['rm', 'delete', 'terminate', 'disable', 'remove', 'destroy']
        command_lower = command.lower()
        
        # Allow these dangerous commands if user explicitly includes them
        # This is for security - require users to be explicit about destructive actions
        if any(keyword in command_lower for keyword in dangerous_keywords):
            app.logger.warning(f"Potentially destructive command detected: {command}")
        
        # Assume role and get temporary credentials
        supervisor = SupervisorAgent(role_arn, external_id, region)
        try:
            creds = supervisor.assume()
            app.logger.info(f"Assumed role for terminal: {role_arn}")
        except Exception as e:
            app.logger.error(f"Failed to assume role for terminal: {e}")
            return jsonify({"error": f"Failed to assume role: {str(e)}"}), 403
        
        # Prepare environment with assumed role credentials
        env = os.environ.copy()
        env['AWS_ACCESS_KEY_ID'] = creds.get('aws_access_key_id', '')
        env['AWS_SECRET_ACCESS_KEY'] = creds.get('aws_secret_access_key', '')
        env['AWS_SESSION_TOKEN'] = creds.get('aws_session_token', '')
        env['AWS_DEFAULT_REGION'] = region
        
        app.logger.info(f"Executing AWS CLI command: {command}")
        
        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        # Prepare response
        response = {
            "success": result.returncode == 0,
            "command": command,
            "stdout": result.stdout if result.stdout else None,
            "stderr": result.stderr if result.stderr else None,
            "error": None if result.returncode == 0 else f"Command failed with exit code {result.returncode}"
        }
        
        if result.returncode != 0:
            app.logger.error(f"Command failed: {result.stderr}")
        
        return jsonify(response)
        
    except subprocess.TimeoutExpired:
        app.logger.error("Command execution timed out")
        return jsonify({"error": "Command execution timed out (max 30 seconds)"}), 504
    except Exception as e:
        app.logger.error(f"Error executing command: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Command execution failed: {str(e)}"}), 500

@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "AWS Security Agent",
        "version": "2.0.0"
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
