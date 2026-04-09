#!/usr/bin/env python3
"""
Phase 2 — Create Bedrock Knowledge Base using Pinecone vector store.

Usage:
    python scripts/create_knowledge_base.py --account 713520983597 --region us-east-1
"""
import argparse
import boto3
import json
import time
from pathlib import Path

PINECONE_API_KEY  = "pcsk_28xbBs_FGLHz4q33V9waMuKxDbKMTzuczN34GDmhCbiMh5FuncDxMvMrDr5usCntbbxiEk"
PINECONE_HOST     = "https://banking-bi-kb-7ujenwa.svc.aped-4627-b74a.pinecone.io"
PINECONE_INDEX    = "banking-bi-kb"


def get_stack_outputs(stack_name: str, region: str) -> dict:
    cf = boto3.client("cloudformation", region_name=region)
    response = cf.describe_stacks(StackName=stack_name)
    return {
        o["OutputKey"]: o["OutputValue"]
        for o in response["Stacks"][0].get("Outputs", [])
    }


def store_pinecone_secret(api_key: str, account: str, region: str) -> str:
    """Store Pinecone API key in Secrets Manager and return the ARN."""
    sm = boto3.client("secretsmanager", region_name=region)
    secret_name = "banking-bi/pinecone/api-key"

    try:
        response = sm.create_secret(
            Name=secret_name,
            Description="Pinecone API key for Bedrock Knowledge Base",
            SecretString=json.dumps({"apiKey": api_key}),
        )
        arn = response["ARN"]
        print(f"  ✅ Pinecone secret created: {arn}")
        return arn
    except sm.exceptions.ResourceExistsException:
        response = sm.describe_secret(SecretId=secret_name)
        arn = response["ARN"]
        # Update the value in case it changed
        sm.put_secret_value(
            SecretId=secret_name,
            SecretString=json.dumps({"apiKey": api_key}),
        )
        print(f"  ✅ Pinecone secret updated: {arn}")
        return arn


def grant_kb_role_secret_access(secret_arn: str, kb_role_name: str, region: str):
    """Allow KB role to read the Pinecone secret."""
    iam = boto3.client("iam", region_name=region)
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "PineconeSecretAccess",
            "Effect": "Allow",
            "Action": ["secretsmanager:GetSecretValue"],
            "Resource": [secret_arn],
        }]
    }
    iam.put_role_policy(
        RoleName=kb_role_name,
        PolicyName="banking-bi-kb-pinecone-secret",
        PolicyDocument=json.dumps(policy),
    )
    print(f"  ✅ IAM policy attached")


def create_knowledge_base(kb_role_arn: str, pinecone_secret_arn: str,
                           region: str) -> str:
    """Create Bedrock Knowledge Base using Pinecone."""
    client = boto3.client("bedrock-agent", region_name=region)

    print(f"\nCreating Bedrock Knowledge Base (Pinecone vector store)...")
    try:
        response = client.create_knowledge_base(
            name="banking-bi-kpi-definitions-v2",
            description=(
                "Governed KPI metric definitions for Banking BI Copilot. "
                "Official formulas for NIM, NPL, CASA, ROE/ROA, CIR, LCR/NSFR."
            ),
            roleArn=kb_role_arn,
            knowledgeBaseConfiguration={
                "type": "VECTOR",
                "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": (
                        f"arn:aws:bedrock:{region}::foundation-model/"
                        "amazon.titan-embed-text-v2:0"
                    )
                }
            },
            storageConfiguration={
                "type": "PINECONE",
                "pineconeConfiguration": {
                    "connectionString": PINECONE_HOST,
                    "credentialsSecretArn": pinecone_secret_arn,
                    "fieldMapping": {
                        "textField": "text",
                        "metadataField": "metadata",
                    }
                }
            }
        )
        kb_id = response["knowledgeBase"]["knowledgeBaseId"]
        print(f"  ✅ Knowledge Base ID: {kb_id}")
        return kb_id

    except client.exceptions.ConflictException:
        print("  Already exists — fetching ID...")
        response = client.list_knowledge_bases()
        for kb in response.get("knowledgeBaseSummaries", []):
            if kb["name"] == "banking-bi-metric-definitions":
                print(f"  Found: {kb['knowledgeBaseId']}")
                return kb["knowledgeBaseId"]
    return None


def wait_for_kb_active(kb_id: str, region: str) -> bool:
    client = boto3.client("bedrock-agent", region_name=region)
    print("  Waiting for Knowledge Base to become ACTIVE...")
    for _ in range(30):
        r = client.get_knowledge_base(knowledgeBaseId=kb_id)
        status = r["knowledgeBase"]["status"]
        print(f"  Status: {status}")
        if status == "ACTIVE":
            return True
        elif status == "FAILED":
            print(f"  FAILED: {r['knowledgeBase'].get('failureReasons')}")
            return False
        time.sleep(10)
    return False


def create_data_source(kb_id: str, bucket_arn: str, region: str) -> str:
    client = boto3.client("bedrock-agent", region_name=region)
    print("\nCreating S3 data source...")
    try:
        response = client.create_data_source(
            knowledgeBaseId=kb_id,
            name="metric-definitions-s3",
            description="Governed KPI metric definition documents",
            dataSourceConfiguration={
                "type": "S3",
                "s3Configuration": {
                    "bucketArn": bucket_arn,
                    "inclusionPrefixes": ["metric-definitions/"]
                }
            },
            vectorIngestionConfiguration={
                "chunkingConfiguration": {
                    "chunkingStrategy": "FIXED_SIZE",
                    "fixedSizeChunkingConfiguration": {
                        "maxTokens": 512,
                        "overlapPercentage": 20
                    }
                }
            }
        )
        ds_id = response["dataSource"]["dataSourceId"]
        print(f"  ✅ Data Source ID: {ds_id}")
        return ds_id
    except Exception as e:
        if "already exists" in str(e).lower():
            response = client.list_data_sources(knowledgeBaseId=kb_id)
            for ds in response.get("dataSourceSummaries", []):
                if ds["name"] == "metric-definitions-s3":
                    print(f"  Already exists: {ds['dataSourceId']}")
                    return ds["dataSourceId"]
        raise


def upload_definitions(bucket_name: str, definitions_dir: str, region: str):
    s3 = boto3.client("s3", region_name=region)
    path = Path(definitions_dir)
    files = list(path.glob("*.md"))
    print(f"\nUploading {len(files)} metric definition files to S3...")
    for f in files:
        key = f"metric-definitions/{f.name}"
        s3.upload_file(str(f), bucket_name, key,
                       ExtraArgs={"ContentType": "text/markdown"})
        print(f"  ✓ {f.name}")


def trigger_ingestion(kb_id: str, ds_id: str, region: str) -> bool:
    client = boto3.client("bedrock-agent", region_name=region)
    print("\nStarting ingestion job...")
    response = client.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id,
        description="Phase 2 initial ingestion",
    )
    job_id = response["ingestionJob"]["ingestionJobId"]
    print(f"  Job ID: {job_id}")
    while True:
        r = client.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            ingestionJobId=job_id,
        )
        status = r["ingestionJob"]["status"]
        stats  = r["ingestionJob"].get("statistics", {})
        print(f"  {status} — indexed: {stats.get('numberOfNewDocumentsIndexed',0)} "
              f"failed: {stats.get('numberOfDocumentsFailed',0)}")
        if status == "COMPLETE":
            print("  ✅ Ingestion complete!")
            return True
        elif status == "FAILED":
            print(f"  ❌ Failed: {r['ingestionJob'].get('failureReasons')}")
            return False
        time.sleep(10)


def save_ids(kb_id: str, ds_id: str):
    with open("kb_ids.json", "w") as f:
        json.dump({"knowledge_base_id": kb_id, "data_source_id": ds_id}, f, indent=2)
    print(f"\n✅ Saved to kb_ids.json — keep this for Phase 3!")
    print(f"   Knowledge Base ID : {kb_id}")
    print(f"   Data Source ID    : {ds_id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True)
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()

    region  = args.region
    account = args.account

    print("Fetching Phase 2 stack outputs...")
    p2_outputs  = get_stack_outputs("BankingBIKnowledgeBase", region)
    bucket_name = p2_outputs["DocsBucketName"]
    kb_role_arn = p2_outputs["KBRoleArn"]
    bucket_arn  = f"arn:aws:s3:::{bucket_name}"
    kb_role_name = "banking-bi-bedrock-kb"

    print(f"  Bucket  : {bucket_name}")
    print(f"  KB Role : {kb_role_arn}")

    # Step 1 — Store Pinecone API key in Secrets Manager
    print("\nStoring Pinecone API key in Secrets Manager...")
    pinecone_secret_arn = store_pinecone_secret(PINECONE_API_KEY, account, region)

    # Step 2 — Grant KB role access to the secret
    print("\nUpdating IAM permissions...")
    grant_kb_role_secret_access(pinecone_secret_arn, kb_role_name, region)

    # Step 3 — Create Knowledge Base
    kb_id = create_knowledge_base(kb_role_arn, pinecone_secret_arn, region)
    if not kb_id:
        print("ERROR: Could not create Knowledge Base")
        return

    # Step 4 — Wait for ACTIVE
    if not wait_for_kb_active(kb_id, region):
        print("ERROR: Knowledge Base did not become ACTIVE")
        return

    # Step 5 — Create data source
    ds_id = create_data_source(kb_id, bucket_arn, region)

    # Step 6 — Upload metric definitions
    script_dir      = Path(__file__).parent
    definitions_dir = script_dir.parent / "metric_definitions"
    upload_definitions(bucket_name, str(definitions_dir), region)

    # Step 7 — Trigger ingestion
    trigger_ingestion(kb_id, ds_id, region)

    # Step 8 — Save IDs for Phase 3
    save_ids(kb_id, ds_id)


if __name__ == "__main__":
    main()
