# test_pipeline.py
from supervisor.supervisor_agent import SupervisorAgent

if __name__ == "__main__":
    # Replace with your actual IAM role for cross-account / least-priv access
    role_arn = "arn:aws:iam::867344463195:role/S3AgentRole"
    external_id = "my-s3-agent-2025"
    region = "us-east-1"

    # Initialize supervisor
    supervisor = SupervisorAgent(role_arn, external_id, region)

    # Step 1: Assume role
    creds = supervisor.assume()
    print("\n=== Temporary Credentials ===")
    for k, v in creds.items():
        print(f"{k}: {v[:8]}...")  # print partially for safety

    # Step 2: Run full scan + fix
    results = supervisor.scan_and_fix()
    print("\n=== Final Results ===")
    for r in results:
        print(r)
