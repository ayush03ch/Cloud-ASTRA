"""
Test script to verify RAG implementation is working correctly
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from agents.utils.rag_security_search import RAGSecuritySearch

def test_rag_initialization():
    """Test RAG system initialization"""
    print("=" * 70)
    print("TEST 1: RAG Initialization")
    print("=" * 70)
    
    rag = RAGSecuritySearch()
    
    print(f"\nRAG Enabled: {rag.enabled}")
    print(f"Documents Loaded: {len(rag.documents)}")
    print(f"Vocabulary Size: {len(rag.vocabulary)}")
    
    if rag.documents:
        print("\nLoaded Documents:")
        for doc_id, doc in rag.documents.items():
            print(f"  - {doc_id}: {doc['title']}")
    
    return rag

def test_s3_encryption_search(rag):
    """Test S3 encryption issue search"""
    print("\n" + "=" * 70)
    print("TEST 2: S3 Encryption Search")
    print("=" * 70)
    
    configuration = {
        'Name': 'test-bucket',
        'Encryption': None,
        'VersioningConfiguration': {'Status': 'Disabled'}
    }
    
    results = rag.search_security_issues(
        service='s3',
        configuration=configuration,
        intent='data_storage',
        top_k=3
    )
    
    print(f"\nFound {len(results)} relevant documents")
    for i, finding in enumerate(results, 1):
        print(f"\n{i}. {finding['title']}")
        print(f"   Relevance Score: {finding['relevance_score']:.3f}")
        print(f"   Source: {finding['source']}")
        print(f"   Keywords: {', '.join(finding['keywords'])}")
    
    return results

def test_ec2_security_group_search(rag):
    """Test EC2 security group issue search"""
    print("\n" + "=" * 70)
    print("TEST 3: EC2 Security Group Search")
    print("=" * 70)
    
    configuration = {
        'GroupId': 'sg-12345',
        'IpPermissions': [
            {
                'FromPort': 22,
                'ToPort': 22,
                'IpProtocol': 'tcp',
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    }
    
    results = rag.search_security_issues(
        service='ec2',
        configuration=configuration,
        intent='web_server',
        top_k=3
    )
    
    print(f"\nFound {len(results)} relevant documents")
    for i, finding in enumerate(results, 1):
        print(f"\n{i}. {finding['title']}")
        print(f"   Relevance Score: {finding['relevance_score']:.3f}")
        print(f"   Sections: {', '.join(finding['sections'].keys())}")
    
    return results

def test_iam_mfa_search(rag):
    """Test IAM MFA issue search"""
    print("\n" + "=" * 70)
    print("TEST 4: IAM MFA Search")
    print("=" * 70)
    
    configuration = {
        'UserName': 'test-user',
        'MFADevices': [],
        'LoginProfile': {'CreateDate': '2024-01-01'}
    }
    
    results = rag.search_security_issues(
        service='iam',
        configuration=configuration,
        intent='strong_security',
        top_k=3
    )
    
    print(f"\nFound {len(results)} relevant documents")
    for i, finding in enumerate(results, 1):
        print(f"\n{i}. {finding['title']}")
        print(f"   Relevance Score: {finding['relevance_score']:.3f}")
    
    return results

def test_lambda_logging_search(rag):
    """Test Lambda logging issue search"""
    print("\n" + "=" * 70)
    print("TEST 5: Lambda Logging Search")
    print("=" * 70)
    
    configuration = {
        'FunctionName': 'test-function',
        'Timeout': 3,
        'MemorySize': 128,
        'Role': 'arn:aws:iam::123456789012:role/lambda-role'
    }
    
    results = rag.search_security_issues(
        service='lambda',
        configuration=configuration,
        intent='api_endpoint',
        top_k=3
    )
    
    print(f"\nFound {len(results)} relevant documents")
    for i, finding in enumerate(results, 1):
        print(f"\n{i}. {finding['title']}")
        print(f"   Relevance Score: {finding['relevance_score']:.3f}")
    
    return results

def main():
    """Run all RAG tests"""
    print("\n" + "█" * 70)
    print("  CloudASTRA RAG System Test Suite")
    print("█" * 70 + "\n")
    
    try:
        # Test 1: Initialize RAG
        rag = test_rag_initialization()
        
        if not rag.enabled:
            print("\n❌ RAG is not enabled. Cannot proceed with tests.")
            print("   Check if knowledge_base directory exists with .txt files")
            return
        
        # Test 2-5: Search tests
        s3_results = test_s3_encryption_search(rag)
        ec2_results = test_ec2_security_group_search(rag)
        iam_results = test_iam_mfa_search(rag)
        lambda_results = test_lambda_logging_search(rag)
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"✓ RAG Initialized: {rag.enabled}")
        print(f"✓ Total Documents: {len(rag.documents)}")
        print(f"✓ S3 Results: {len(s3_results)}")
        print(f"✓ EC2 Results: {len(ec2_results)}")
        print(f"✓ IAM Results: {len(iam_results)}")
        print(f"✓ Lambda Results: {len(lambda_results)}")
        
        total_results = len(s3_results) + len(ec2_results) + len(iam_results) + len(lambda_results)
        
        if total_results > 0:
            print(f"\n✅ RAG is working correctly! Found {total_results} total relevant documents.")
        else:
            print("\n⚠️  RAG found no relevant documents. Check knowledge base content.")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
