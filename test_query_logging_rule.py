#!/usr/bin/env python3
"""
Simple test script for Query Logging Rule - the most basic Route53 rule
This test directly invokes the rule without the full supervisor framework
"""

import boto3
from agents.route53_agent.rules.query_logging_rule import QueryLoggingRule

def test_query_logging_rule():
    """Test the query logging rule against your AWS account."""
    
    print("="*70)
    print("Testing Query Logging Rule - Route53 Agent")
    print("="*70)
    
    # Step 1: Create Route53 client (uses your AWS CLI credentials)
    print("\n[Step 1] Creating Route53 client...")
    try:
        client = boto3.client('route53')
        print("✅ Route53 client created successfully")
    except Exception as e:
        print(f"❌ Failed to create client: {e}")
        print("Make sure you've run 'aws configure' first")
        return
    
    # Step 2: List all hosted zones
    print("\n[Step 2] Listing hosted zones in your account...")
    try:
        response = client.list_hosted_zones()
        zones = response.get('HostedZones', [])
        
        if not zones:
            print("❌ No hosted zones found!")
            print("Create a hosted zone first:")
            print("  aws route53 create-hosted-zone --name testdomain.example.com --caller-reference test123")
            return
        
        print(f"✅ Found {len(zones)} hosted zone(s):")
        for i, zone in enumerate(zones, 1):
            zone_id = zone['Id'].split('/')[-1]
            zone_name = zone['Name']
            is_private = zone.get('Config', {}).get('PrivateZone', False)
            zone_type = "Private" if is_private else "Public"
            print(f"   {i}. {zone_name} ({zone_type}) - ID: {zone_id}")
        
    except Exception as e:
        print(f"❌ Failed to list zones: {e}")
        return
    
    # Step 3: Initialize the Query Logging Rule
    print("\n[Step 3] Initializing Query Logging Rule...")
    rule = QueryLoggingRule()
    print(f"✅ Rule initialized: {rule.id}")
    print(f"   Detection: {rule.detection}")
    print(f"   Auto-safe: {rule.auto_safe}")
    print(f"   Can auto-fix: {rule.can_auto_fix}")
    
    # Step 4: Test the rule against each hosted zone
    print("\n[Step 4] Running rule check on all hosted zones...")
    print("="*70)
    
    findings = []
    
    for zone in zones:
        zone_id = zone['Id']
        zone_name = zone['Name']
        
        print(f"\n🔍 Checking: {zone_name}")
        print(f"   Zone ID: {zone_id}")
        
        try:
            # Run the rule check
            has_issue = rule.check(client, zone_id, zone_name)
            
            if has_issue:
                print(f"   ⚠️  ISSUE DETECTED: Query logging is disabled")
                findings.append({
                    'zone_name': zone_name,
                    'zone_id': zone_id,
                    'issue': rule.detection
                })
            else:
                print(f"   ✅ PASSED: Query logging is enabled")
                
        except Exception as e:
            print(f"   ❌ Error checking zone: {e}")
    
    # Step 5: Display results summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    
    if findings:
        print(f"\n📋 Issues Found: {len(findings)}")
        print(f"🔴 Severity: Medium")
        print(f"\nZones with Query Logging Disabled:")
        
        for i, finding in enumerate(findings, 1):
            print(f"\n{i}. {finding['zone_name']}")
            print(f"   Zone ID: {finding['zone_id']}")
            print(f"   Issue: {finding['issue']}")
        
        # Show fix instructions
        print("\n" + "="*70)
        print("FIX INSTRUCTIONS")
        print("="*70)
        print()
        for instruction in rule.fix_instructions:
            print(instruction)
        
    else:
        print("\n✅ All zones passed! Query logging is enabled on all zones.")
    
    print("\n" + "="*70)
    print("Test Complete!")
    print("="*70)

if __name__ == "__main__":
    test_query_logging_rule()
