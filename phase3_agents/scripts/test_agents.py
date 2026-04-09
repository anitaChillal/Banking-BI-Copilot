#!/usr/bin/env python3
"""
Phase 3 — Test the full agent pipeline.
Usage:
    python scripts/test_agents.py --region us-east-1
    python scripts/test_agents.py --region us-east-1 --message "Why did our NIM drop this week?"
    python scripts/test_agents.py --region us-east-1 --trigger anomaly --kpi nim
"""
import argparse
import boto3
import json

def test_pipeline(region: str, message: str = None,
                  trigger: str = "manual", kpi: str = None):
    lambda_client = boto3.client("lambda", region_name=region)

    if trigger == "anomaly":
        payload = {
            "source": "banking-bi.etl",
            "detail-type": "KPI Anomaly Detected",
            "detail": {
                "kpi_name": kpi or "nim",
                "severity": "High",
                "change_bps": -35,
            }
        }
    elif message:
        payload = {
            "httpMethod": "POST",
            "body": json.dumps({
                "message": message,
            })
        }
    else:
        payload = {
            "trigger": "manual",
            "kpis": ["nim", "npl_ratio", "casa_ratio",
                     "roe_roa", "cost_income", "lcr_nsfr"],
        }

    print(f"Invoking supervisor Lambda...")
    print(f"Trigger: {trigger}")
    if message:
        print(f"Message: {message}")
    print("-" * 60)

    response = lambda_client.invoke(
        FunctionName="banking-bi-supervisor",
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode(),
    )

    result = json.loads(response["Payload"].read())

    if response.get("FunctionError"):
        print(f"❌ Error: {result}")
        return

    print(f"✅ Session ID: {result.get('session_id')}")

    if result.get("response"):
        print(f"\nAgent Response:\n{result['response'][:1000]}")

    body = result.get("body")
    if body:
        try:
            body_parsed = json.loads(body)
            print(f"\nResponse: {json.dumps(body_parsed, indent=2)[:500]}")
        except Exception:
            print(f"\nResponse: {body[:500]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--message", help="Conversational message to send")
    parser.add_argument("--trigger", default="manual",
                        choices=["manual", "anomaly", "conversational"])
    parser.add_argument("--kpi", help="KPI for anomaly trigger")
    args = parser.parse_args()

    test_pipeline(args.region, args.message, args.trigger, args.kpi)


if __name__ == "__main__":
    main()
