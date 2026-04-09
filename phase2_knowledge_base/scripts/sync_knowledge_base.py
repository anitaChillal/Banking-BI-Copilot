#!/usr/bin/env python3
"""
Phase 2 — Upload metric definitions to S3 and trigger Bedrock KB ingestion.
Run after CDK deploy completes.

Usage:
    python scripts/sync_knowledge_base.py --account 713520983597 --region us-east-1
"""
import argparse
import boto3
import os
import time
import json
from pathlib import Path

def upload_metric_definitions(bucket_name: str, definitions_dir: str, region: str):
    """Upload all metric definition markdown files to S3."""
    s3 = boto3.client("s3", region_name=region)
    uploaded = []

    definitions_path = Path(definitions_dir)
    md_files = list(definitions_path.glob("*.md"))

    if not md_files:
        print(f"No .md files found in {definitions_dir}")
        return uploaded

    print(f"\nUploading {len(md_files)} metric definition files to s3://{bucket_name}/metric-definitions/")

    for md_file in md_files:
        s3_key = f"metric-definitions/{md_file.name}"
        s3.upload_file(
            str(md_file),
            bucket_name,
            s3_key,
            ExtraArgs={"ContentType": "text/markdown"},
        )
        print(f"  ✓ Uploaded {md_file.name} → {s3_key}")
        uploaded.append(s3_key)

    print(f"\nUploaded {len(uploaded)} files successfully.")
    return uploaded


def get_kb_details(stack_name: str, region: str):
    """Retrieve Knowledge Base ID and Data Source ID from CloudFormation outputs."""
    cf = boto3.client("cloudformation", region_name=region)
    response = cf.describe_stacks(StackName=stack_name)
    outputs = {
        o["OutputKey"]: o["OutputValue"]
        for o in response["Stacks"][0].get("Outputs", [])
    }
    return (
        outputs.get("KnowledgeBaseId"),
        outputs.get("DataSourceId"),
        outputs.get("MetricDocsBucket"),
    )


def trigger_ingestion(kb_id: str, ds_id: str, region: str):
    """Start a Bedrock Knowledge Base ingestion job."""
    bedrock_agent = boto3.client("bedrock-agent", region_name=region)

    print(f"\nStarting ingestion job for Knowledge Base: {kb_id}")
    print(f"Data Source: {ds_id}")

    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id,
        description="Initial metric definition ingestion — Phase 2 setup",
    )

    job_id = response["ingestionJob"]["ingestionJobId"]
    print(f"Ingestion job started: {job_id}")
    return job_id


def wait_for_ingestion(kb_id: str, ds_id: str, job_id: str, region: str):
    """Poll until ingestion job completes."""
    bedrock_agent = boto3.client("bedrock-agent", region_name=region)

    print("\nWaiting for ingestion to complete...")
    while True:
        response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            ingestionJobId=job_id,
        )
        status = response["ingestionJob"]["status"]
        stats = response["ingestionJob"].get("statistics", {})

        print(f"  Status: {status} | "
              f"Scanned: {stats.get('numberOfDocumentsScanned', 0)} | "
              f"Indexed: {stats.get('numberOfNewDocumentsIndexed', 0)} | "
              f"Failed: {stats.get('numberOfDocumentsFailed', 0)}")

        if status == "COMPLETE":
            print("\n✅ Ingestion complete!")
            print(json.dumps(stats, indent=2))
            return True
        elif status == "FAILED":
            failures = response["ingestionJob"].get("failureReasons", [])
            print(f"\n❌ Ingestion failed: {failures}")
            return False

        time.sleep(10)


def test_knowledge_base(kb_id: str, region: str):
    """Run a test query against the Knowledge Base to verify it works."""
    bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=region)

    test_queries = [
        "What is the formula for Net Interest Margin?",
        "When is a loan classified as non-performing?",
        "What are the HQLA Level 1 assets for LCR calculation?",
    ]

    print("\n--- Testing Knowledge Base retrieval ---")
    for query in test_queries:
        print(f"\nQuery: {query}")
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": 2}
            },
        )
        results = response.get("retrievalResults", [])
        if results:
            top = results[0]
            score = top.get("score", 0)
            text = top.get("content", {}).get("text", "")[:200]
            print(f"  Score: {score:.4f}")
            print(f"  Excerpt: {text}...")
        else:
            print("  No results returned.")


def main():
    parser = argparse.ArgumentParser(description="Sync metric definitions to Bedrock KB")
    parser.add_argument("--account", required=True, help="AWS account ID")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--skip-upload", action="store_true", help="Skip S3 upload")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip ingestion trigger")
    parser.add_argument("--test-only", action="store_true", help="Only run test queries")
    args = parser.parse_args()

    stack_name = "BankingBIKnowledgeBase"
    region = args.region

    # Get KB details from CloudFormation
    print(f"Retrieving stack outputs from {stack_name}...")
    kb_id, ds_id, bucket_name = get_kb_details(stack_name, region)

    if not kb_id:
        print("ERROR: Could not find KnowledgeBaseId in stack outputs.")
        print("Make sure the BankingBIKnowledgeBase stack is deployed.")
        return

    print(f"Knowledge Base ID : {kb_id}")
    print(f"Data Source ID    : {ds_id}")
    print(f"S3 Bucket         : {bucket_name}")

    if args.test_only:
        test_knowledge_base(kb_id, region)
        return

    # Upload metric definitions
    if not args.skip_upload:
        script_dir = Path(__file__).parent
        definitions_dir = script_dir.parent / "metric_definitions"
        upload_metric_definitions(bucket_name, str(definitions_dir), region)

    # Trigger ingestion
    if not args.skip_ingest:
        job_id = trigger_ingestion(kb_id, ds_id, region)
        success = wait_for_ingestion(kb_id, ds_id, job_id, region)

        if success:
            # Run test queries
            test_knowledge_base(kb_id, region)


if __name__ == "__main__":
    main()
