"""
Seed LocalStack with demo AWS resources.

Creates:
  - S3 bucket "aegis-demo-logs" with 5 sample log objects
  - CloudWatch Logs group /aegis/demo/api with a retention policy
  - EC2: 3 tagged demo instances via AMI Moto defaults
  - IAM: a read-only role "aegis-demo-readonly"

Usage:
    python seed_localstack.py [--endpoint http://localhost:4566]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

try:
    import boto3  # type: ignore
    from botocore.exceptions import ClientError  # type: ignore
except ImportError:
    print("[seed_localstack] boto3 required: pip install boto3", file=sys.stderr)
    sys.exit(1)


def client(service: str, endpoint: str):
    return boto3.client(
        service,
        endpoint_url=endpoint,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


def seed_s3(endpoint: str) -> None:
    s3 = client("s3", endpoint)
    bucket = "aegis-demo-logs"
    try:
        s3.create_bucket(Bucket=bucket)
    except ClientError as e:
        if "BucketAlreadyOwnedByYou" not in str(e):
            raise
    for i in range(5):
        key = f"logs/2026-04-{20+i:02d}/app.log"
        body = f"2026-04-{20+i:02d}T09:00:00Z INFO demo entry {i}\n"
        s3.put_object(Bucket=bucket, Key=key, Body=body.encode())
    print(f"[seed_localstack] S3: seeded 5 objects into {bucket}")


def seed_logs(endpoint: str) -> None:
    logs = client("logs", endpoint)
    group = "/aegis/demo/api"
    try:
        logs.create_log_group(logGroupName=group)
    except ClientError as e:
        if "ResourceAlreadyExists" not in str(e):
            raise
    logs.put_retention_policy(logGroupName=group, retentionInDays=7)
    stream = "demo-stream-001"
    try:
        logs.create_log_stream(logGroupName=group, logStreamName=stream)
    except ClientError as e:
        if "ResourceAlreadyExists" not in str(e):
            raise
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    logs.put_log_events(
        logGroupName=group,
        logStreamName=stream,
        logEvents=[{"timestamp": ts, "message": "demo startup log"}],
    )
    print(f"[seed_localstack] Logs: created group {group}")


def seed_ec2(endpoint: str) -> None:
    ec2 = client("ec2", endpoint)
    try:
        images = ec2.describe_images(Owners=["amazon"])
        ami = images["Images"][0]["ImageId"] if images["Images"] else "ami-12345678"
    except Exception:
        ami = "ami-12345678"
    res = ec2.run_instances(
        ImageId=ami,
        MinCount=3,
        MaxCount=3,
        InstanceType="t3.micro",
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [
                {"Key": "aegis:demo", "Value": "true"},
                {"Key": "Environment", "Value": "demo"},
            ],
        }],
    )
    print(f"[seed_localstack] EC2: launched {len(res['Instances'])} demo instances")


def seed_iam(endpoint: str) -> None:
    iam = client("iam", endpoint)
    role_name = "aegis-demo-readonly"
    trust = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    }
    try:
        iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust))
    except ClientError as e:
        if "EntityAlreadyExists" not in str(e):
            raise
    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn="arn:aws:iam::aws:policy/ReadOnlyAccess",
    )
    print(f"[seed_localstack] IAM: role {role_name} ready")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://localhost:4566")
    args = ap.parse_args()

    seed_s3(args.endpoint)
    seed_logs(args.endpoint)
    seed_ec2(args.endpoint)
    seed_iam(args.endpoint)
    print("[seed_localstack] done")


if __name__ == "__main__":
    main()
