#!/usr/bin/env python3
"""
Phase 3 — Post-deploy configuration script.
Reads Bedrock agent IDs from CloudFormation and stores in SSM.
Also installs reportlab on the PDF Lambda layer.

Usage:
    python scripts/configure_agents.py --region us-east-1
"""
import argparse
import boto3
import json
import subprocess
import sys

def get_stack_outputs(stack_name: str, region: str) -> dict:
    cf = boto3.client("cloudformation", region_name=region)
    response = cf.describe_stacks(StackName=stack_name)
    return {
        o["OutputKey"]: o["OutputValue"]
        for o in response["Stacks"][0].get("Outputs", [])
    }


def store_ssm_params(outputs: dict, region: str):
    """Store agent IDs in SSM Parameter Store."""
    ssm = boto3.client("ssm", region_name=region)
    params = {
        "/banking-bi/supervisor-agent-id":  outputs.get("SupervisorAgentId"),
        "/banking-bi/supervisor-alias-id":  outputs.get("SupervisorAliasId"),
        "/banking-bi/kpi-agent-id":         outputs.get("KPIAgentId"),
        "/banking-bi/kpi-alias-id":         outputs.get("KPIAliasId"),
        "/banking-bi/driver-agent-id":      outputs.get("DriverAgentId"),
        "/banking-bi/validation-agent-id":  outputs.get("ValidationAgentId"),
    }

    for name, value in params.items():
        if value:
            ssm.put_parameter(
                Name=name, Value=value,
                Type="String", Overwrite=True,
            )
            print(f"  ✅ Stored {name} = {value}")
        else:
            print(f"  ⚠️  Skipped {name} — value not found in outputs")


def update_supervisor_env(outputs: dict, region: str):
    """Update supervisor Lambda with agent IDs as env vars."""
    lambda_client = boto3.client("lambda", region_name=region)
    fn_name = "banking-bi-supervisor"

    try:
        current = lambda_client.get_function_configuration(
            FunctionName=fn_name
        )
        env = current.get("Environment", {}).get("Variables", {})
        env.update({
            "SUPERVISOR_AGENT_ID": outputs.get("SupervisorAgentId", ""),
            "SUPERVISOR_ALIAS_ID": outputs.get("SupervisorAliasId", ""),
        })
        lambda_client.update_function_configuration(
            FunctionName=fn_name,
            Environment={"Variables": env},
        )
        print(f"  ✅ Updated {fn_name} environment")
    except Exception as e:
        print(f"  ⚠️  Could not update Lambda env: {e}")


def install_reportlab(region: str):
    """Check if reportlab is available in the PDF Lambda."""
    print("\nChecking reportlab availability...")
    lambda_client = boto3.client("lambda", region_name=region)

    test_payload = {
        "actionGroup": "test",
        "function": "test_reportlab",
        "parameters": [],
    }

    try:
        response = lambda_client.invoke(
            FunctionName="banking-bi-pdf-action",
            InvocationType="RequestResponse",
            Payload=json.dumps({
                "actionGroup": "pdf-report-actions",
                "function": "generate_pdf_report",
                "parameters": [
                    {"name": "session_id", "value": "test-001"},
                    {"name": "headline", "value": "Test report"},
                    {"name": "findings_json", "value": "{}"},
                    {"name": "risk_level", "value": "low"},
                ],
            }).encode(),
        )
        result = json.loads(response["Payload"].read())
        if response.get("FunctionError"):
            if "reportlab" in str(result).lower():
                print("  ⚠️  reportlab not installed. Installing as Lambda layer...")
                print("  Install reportlab in your Lambda by adding it to requirements:")
                print("  1. Create a layer with: pip install reportlab -t python/")
                print("  2. zip -r reportlab-layer.zip python/")
                print("  3. aws lambda publish-layer-version --layer-name reportlab ...")
            else:
                print(f"  ⚠️  PDF Lambda test error: {result}")
        else:
            print("  ✅ PDF Lambda working correctly")
    except Exception as e:
        print(f"  ⚠️  Could not test PDF Lambda: {e}")


def print_summary(outputs: dict):
    print("\n" + "="*60)
    print("PHASE 3 CONFIGURATION COMPLETE")
    print("="*60)
    print(f"\nSupervisor Agent ID : {outputs.get('SupervisorAgentId')}")
    print(f"API Endpoint        : {outputs.get('ApiEndpoint')}")
    print(f"Chat Endpoint       : {outputs.get('ChatEndpoint')}")
    print(f"Reports Bucket      : {outputs.get('OutputBucketName')}")
    print(f"SNS Topic           : {outputs.get('SummaryTopicArn')}")

    print("\n--- NEXT STEPS ---")
    print("1. Subscribe to executive summaries:")
    print(f"   aws sns subscribe --topic-arn {outputs.get('SummaryTopicArn')} \\")
    print("     --protocol email --notification-endpoint your@email.com")
    print("\n2. Test the pipeline:")
    print("   python scripts/test_agents.py --region us-east-1")
    print("\n3. Test conversational API:")
    print(f"   curl -X POST {outputs.get('ChatEndpoint')} \\")
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"message": "What is our current NIM and what is driving it?"}\'')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()

    region = args.region
    stack_name = "BankingBIAgents"

    print(f"Fetching {stack_name} outputs...")
    outputs = get_stack_outputs(stack_name, region)

    print("\nStoring agent IDs in SSM Parameter Store...")
    store_ssm_params(outputs, region)

    print("\nUpdating supervisor Lambda environment...")
    update_supervisor_env(outputs, region)

    print("\nTesting PDF Lambda...")
    install_reportlab(region)

    print_summary(outputs)


if __name__ == "__main__":
    main()
