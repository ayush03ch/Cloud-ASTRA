# test_route53_agent.py

"""
Test script for Route53 Agent
Run this to test the Route53 security scanning functionality
"""

from supervisor.supervisor_agent import SupervisorAgent

if __name__ == "__main__":
    # Replace with your actual IAM role
    role_arn = "arn:aws:iam::YOUR_ACCOUNT_ID:role/SecurityAgentRole"
    external_id = "my-cloud-astra-role"
    region = "us-east-1"

    # Initialize supervisor
    supervisor = SupervisorAgent(role_arn, external_id, region)
    
    # Optional: User intent input for specific hosted zones
    # Provide intent per zone (by zone ID or zone name)
    user_intent_input = {
        # "example.com.": "public_website",
        # "api.myservice.com.": "api_service",
        # "Z1234567890ABC": "email_domain",  # By zone ID
        # "_global_intent": "public_website"  # Global intent for all zones
    }

    print("="*60)
    print("Route53 Security Scan - Cloud ASTRA")
    print("="*60)

    # Step 1: Assume role
    try:
        creds = supervisor.assume()
        print("\n✅ Successfully assumed role")
        print(f"Access Key: {creds['aws_access_key_id'][:8]}...")
    except Exception as e:
        print(f"\n❌ Failed to assume role: {e}")
        print("\nPlease ensure:")
        print("1. Your AWS credentials are configured")
        print("2. The IAM role exists and has Route53 permissions")
        print("3. The trust policy allows your account to assume the role")
        exit(1)

    # Step 2: Run Route53 security scan
    print("\n" + "="*60)
    print("Starting Route53 Security Scan...")
    print("="*60 + "\n")
    
    try:
        results = supervisor.scan_and_fix(
            user_intent_input=user_intent_input,
            service='route53'  # Scan only Route53
        )
        
        print("\n" + "="*60)
        print("Scan Results Summary")
        print("="*60)
        
        # Extract findings
        findings = results.get('findings', {})
        route53_findings = findings.get('route53', [])
        
        print(f"\n📋 Total Route53 Issues Found: {len(route53_findings)}")
        
        # Count by severity
        critical = sum(1 for f in route53_findings if f.get('severity') == 'critical')
        high = sum(1 for f in route53_findings if f.get('severity') == 'high')
        medium = sum(1 for f in route53_findings if f.get('severity') == 'medium')
        low = sum(1 for f in route53_findings if f.get('severity') == 'low')
        
        print(f"\n🔴 Critical: {critical}")
        print(f"🟠 High: {high}")
        print(f"🟡 Medium: {medium}")
        print(f"🟢 Low: {low}")
        
        # Auto-fixes
        auto_fixes = results.get('auto_fixes_applied', [])
        pending_fixes = results.get('pending_fixes', [])
        
        print(f"\n✅ Auto-fixes Applied: {len(auto_fixes)}")
        print(f"⏳ Pending Manual Fixes: {len(pending_fixes)}")
        
        # Show detailed findings
        if route53_findings:
            print("\n" + "="*60)
            print("Detailed Findings")
            print("="*60)
            
            for idx, finding in enumerate(route53_findings, 1):
                zone_name = finding.get('resource', 'Unknown')
                issue = finding.get('issue', 'Unknown issue')
                severity = finding.get('severity', 'medium').upper()
                source = finding.get('source', 'unknown')
                tier = finding.get('tier', 0)
                
                print(f"\n{idx}. {zone_name}")
                print(f"   Issue: {issue}")
                print(f"   Severity: {severity}")
                print(f"   Detection: Tier {tier} ({source})")
                
                # Show fix instructions if available
                fix_instructions = finding.get('fix_instructions')
                if fix_instructions:
                    print("   Fix Instructions:")
                    for instruction in fix_instructions[:3]:  # Show first 3 lines
                        print(f"     {instruction}")
                    if len(fix_instructions) > 3:
                        print(f"     ... ({len(fix_instructions) - 3} more lines)")
        
        # Show auto-fixes applied
        if auto_fixes:
            print("\n" + "="*60)
            print("Auto-Fixes Applied")
            print("="*60)
            
            for fix in auto_fixes:
                print(f"\n✅ {fix.get('resource', 'Unknown')}")
                print(f"   Fix: {fix.get('issue', 'Unknown')}")
                print(f"   Status: {fix.get('status', 'unknown')}")
        
        # Show pending fixes
        if pending_fixes:
            print("\n" + "="*60)
            print("Pending Manual Fixes")
            print("="*60)
            
            for fix in pending_fixes:
                print(f"\n⏳ {fix.get('resource', 'Unknown')}")
                print(f"   Issue: {fix.get('issue', 'Unknown')}")
                if fix.get('can_auto_fix'):
                    print(f"   Note: Can be auto-fixed with user approval")
        
        print("\n" + "="*60)
        print("🎉 Route53 Security Scan Complete!")
        print("="*60)
        
        # Summary statistics
        summary = results.get('summary', {})
        if summary:
            print(f"\nTotal Findings: {summary.get('total_findings', 0)}")
            print(f"Auto-Fixable: {summary.get('auto_fixable', 0)}")
            print(f"Fixes Applied: {summary.get('fixes_applied', 0)}")
            print(f"Pending Manual: {summary.get('pending_manual', 0)}")
        
    except Exception as e:
        print(f"\n❌ Scan failed: {e}")
        import traceback
        traceback.print_exc()
