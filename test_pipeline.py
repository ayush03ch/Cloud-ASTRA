# test_pipeline.py
from supervisor.supervisor_agent import SupervisorAgent

if __name__ == "__main__":
    # Replace with your actual IAM role for cross-account / least-priv access
    role_arn = "arn:aws:iam::867344463195:role/S3AgentRole"
    external_id = "my-s3-agent-2025"
    region = "us-east-1"

    # Initialize supervisor
    supervisor = SupervisorAgent(role_arn, external_id, region)
    
    # Optional: User intent input
    # Specify intent per bucket to guide the analysis
    user_intent_input = {
        # "my-website-bucket": "website hosting",
        # "my-data-bucket": "data storage", 
        # "my-archive-bucket": "archival"
        # Leave empty for auto-detection
    }

    # Step 1: Assume role
    creds = supervisor.assume()
    print("\n=== Temporary Credentials ===")
    for k, v in creds.items():
        print(f"{k}: {v[:8]}...")  # print partially for safety

    # Step 2: Run intent-aware scan + fix
    results = supervisor.scan_and_fix(user_intent_input=user_intent_input)
    print("\n=== Final Results ===")
    print(f"📋 Findings: {len(results['findings'].get('s3', []))} S3 issues found")
    print(f"✅ Auto-fixes applied: {len(results['auto_fixes_applied'])}")
    print(f"⚠️ Pending manual fixes: {len(results['pending_fixes'])}")
    
    if results['auto_fixes_applied']:
        print("\n🔧 Auto-fixes Applied:")
        for fix in results['auto_fixes_applied']:
            print(f"  - {fix['resource']}: {fix['status']}")
            
    if results['pending_fixes']:
        print("\n⏳ Pending Manual Fixes:")
        for fix in results['pending_fixes']:
            print(f"  - {fix['resource']}: {fix['issue']}")
    
    print(f"\n🎉 Security scan complete!")
