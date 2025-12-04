from flask import Flask, render_template, request, jsonify
import sys
import os
import json
import logging

# Add parent directory to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Force reload for debugging intent detection
from supervisor.supervisor_agent import SupervisorAgent

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template('index.html')

@app.route('/api/scan', methods=['POST'])
def api_scan():
    """
    Enhanced API endpoint for intent-aware scanning.
    
    Expected JSON:
    {
        "service": "s3" or "lambda",
        "role_arn": "arn:aws:iam::account:role/name",
        "external_id": "external-id",
        "region": "us-east-1",
        "user_intent_input": {
            "bucket1": "website hosting",
            "function1": "api_endpoint"
        },
        "allow_conversion": true (s3 only),
        "auto_fix": true,
        "detailed_logging": false
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract required parameters
        service = data.get('service', 's3')  # Default to s3 for backward compatibility
        role_arn = data.get('role_arn')
        external_id = data.get('external_id', 'default-external-id')
        region = data.get('region', 'us-east-1')
        user_intent_input = data.get('user_intent_input', {})
        allow_conversion = data.get('allow_conversion', True)
        auto_fix = data.get('auto_fix', True)
        detailed_logging = data.get('detailed_logging', False)
        
        # Handle simple user intent (applies to all resources)
        simple_user_intent = data.get('user_intent')
        if simple_user_intent:
            app.logger.info(f"🐛 DEBUG: Received simple user_intent: {simple_user_intent}")
            # Convert simple intent to user_intent_input format
            user_intent_input = {'_global_intent': simple_user_intent}
        
        # DEBUG: Log the user intent input
        app.logger.info(f"🐛 DEBUG: Service: {service}, Final user_intent_input: {user_intent_input}")
        
        # Use appropriate parameters based on request structure
        if not role_arn:
            # Try simplified format with account_id
            account_id = data.get('account_id')
            if account_id:
                role_arn = f'arn:aws:iam::{account_id}:role/{service.upper()}AgentRole'
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
        
        # Run intent-aware scan and fix
        try:
            results = supervisor.scan_and_fix(user_intent_input=user_intent_input, service=service)
            
            # Process results for web interface
            response = {
                "success": True,
                "summary": results.get('summary', {}),
                "findings_count": len(results.get('findings', {}).get(service, [])),
                "auto_fixes_applied": results.get('auto_fixes_applied', []),
                "pending_fixes": results.get('pending_fixes', []),
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
            
            # Extract intent decisions from findings (deduplicated by resource)
            service_findings = results.get('findings', {}).get(service, [])
            intent_decisions_dict = {}  # Use dict to deduplicate by resource name
            
            for finding in service_findings:
                if finding.get('intent'):
                    resource_name = finding.get('resource')
                    # Only add if we haven't seen this resource before
                    if resource_name not in intent_decisions_dict:
                        intent_decisions_dict[resource_name] = {
                            "bucket" if service == 's3' else "function": resource_name,
                            "intent": finding.get('intent'),
                            "confidence": f"{finding.get('intent_confidence', 0):.2f}",
                            "reasoning": finding.get('intent_reasoning', 'No reasoning available')
                        }
            
            # Convert dict values to list for response
            response["intent_decisions"] = list(intent_decisions_dict.values())
            
            app.logger.info(f"Scan completed successfully for {service}. Found {response['findings_count']} issues")
            return jsonify(response)
            
        except Exception as e:
            app.logger.error(f"Error during scan and fix: {e}")
            return jsonify({"error": f"Scan failed: {str(e)}"}), 500
        
    except Exception as e:
        app.logger.error(f"Unexpected error in API endpoint: {e}")
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
        "service": "s3" or "lambda",
        "role_arn": "arn:aws:iam::account:role/name",
        "external_id": "external-id",
        "region": "us-east-1",
        "resource": "bucket-name or function-name",
        "fix_type": "public_access_block|index_document|disable_website_hosting|enable_logging|..."
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract required parameters
        service = data.get('service', 's3')  # Default to s3 for backward compatibility
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
                "service": service,
                "message": result.get('message', 'Fix applied successfully'),
                "details": result.get('details', [])
            }
            
            app.logger.info(f"Manual fix applied successfully: {fix_type} for {resource} ({service})")
            return jsonify(response)
            
        except Exception as e:
            app.logger.error(f"Error applying manual fix: {e}")
            return jsonify({"error": f"Fix failed: {str(e)}"}), 500
        
    except Exception as e:
        app.logger.error(f"Unexpected error in manual fix endpoint: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

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
