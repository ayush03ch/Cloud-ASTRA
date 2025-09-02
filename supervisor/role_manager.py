# supervisor/role_manager.py

import boto3
# from supervisor.config import SESSION_DURATION

def assume_role(role_arn, external_id, region):
    """
    Assume an IAM Role in the target AWS account.
    Returns temporary credentials dictionary.
    """
    sts_client = boto3.client("sts", region_name=region)

    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName="SupervisorAgentSession",
        ExternalId=external_id,
        # DurationSeconds=SESSION_DURATION
    )

    creds = response["Credentials"]
    return {
        "aws_access_key_id": creds["AccessKeyId"],
        "aws_secret_access_key": creds["SecretAccessKey"],
        "aws_session_token": creds["SessionToken"],
        "region": region
    }
