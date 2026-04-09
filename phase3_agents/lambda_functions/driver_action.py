"""
Driver Analysis Action Lambda — Bedrock Agent action group handler.
"""
import json, os, boto3
from datetime import datetime, timezone

bedrock = boto3.client("bedrock-runtime", region_name=os.environ["REGION"])
MODEL_ID = os.environ["MODEL_ID"]
RDS_SECRET_ARN = os.environ["RDS_SECRET_ARN"]
RDS_DB_NAME = os.environ["RDS_DB_NAME"]


def get_db_arn():
    for db in boto3.client("rds").describe_db_instances()["DBInstances"]:
        if "bankingbi" in db["DBInstanceIdentifier"].lower():
            return db["DBInstanceArn"]
    raise ValueError("RDS not found")


def run_sql(sql):
    try:
        r = boto3.client("rds-data").execute_statement(
            resourceArn=get_db_arn(), secretArn=RDS_SECRET_ARN,
            database=RDS_DB_NAME, sql=sql, formatRecordsAs="JSON",
        )
        return json.loads(r.get("formattedRecords", "[]"))
    except Exception as e:
        return []


def analyse_drivers(kpi_name: str, change_direction: str) -> dict:
    segment_data = {}

    if kpi_name == "nim":
        segment_data["by_bu"] = run_sql("""
            SELECT b.bu_type, AVG(l.interest_rate) as avg_rate,
                   SUM(l.interest_income) as income
            FROM fact.loan_position l
            JOIN dim.business_unit b ON b.bu_key = l.bu_key
            GROUP BY b.bu_type ORDER BY income DESC LIMIT 8""")
        segment_data["deposit_cost"] = run_sql("""
            SELECT d.deposit_type, AVG(d.interest_rate) as cost,
                   SUM(d.balance) as balance
            FROM fact.deposit_position d
            GROUP BY d.deposit_type ORDER BY balance DESC LIMIT 8""")

    elif kpi_name == "npl_ratio":
        segment_data["by_product"] = run_sql("""
            SELECT p.product_type, p.asset_class,
                   COUNT(*) as npl_count,
                   SUM(l.outstanding_balance) as npl_balance,
                   AVG(l.days_past_due) as avg_dpd
            FROM fact.loan_position l
            JOIN dim.product p ON p.product_key = l.product_key
            WHERE l.loan_status = 'NPL'
            GROUP BY p.product_type, p.asset_class
            ORDER BY npl_balance DESC LIMIT 8""")

    elif kpi_name == "casa_ratio":
        segment_data["by_segment"] = run_sql("""
            SELECT s.segment_name, d.deposit_type,
                   SUM(d.balance) as balance,
                   SUM(d.number_of_accounts) as accounts
            FROM fact.deposit_position d
            JOIN dim.customer_segment s ON s.segment_key = d.bu_key
            GROUP BY s.segment_name, d.deposit_type
            ORDER BY balance DESC LIMIT 8""")

    # Use Claude to interpret the data
    prompt = f"""You are a banking analytics expert.
KPI: {kpi_name.upper()}
Direction of change: {change_direction}
Segment data: {json.dumps(segment_data, default=str)[:2000]}

Identify the top 3 drivers of this KPI movement. For each return:
- driver: clear description
- confidence: high/medium/low
- evidence: specific data point
- affected_kpis: list

Return a JSON array only."""

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    raw = json.loads(response["body"].read())["content"][0]["text"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        drivers = json.loads(raw.strip())
    except Exception:
        drivers = []

    return {"kpi": kpi_name, "drivers": drivers, "segment_data": segment_data}


def handler(event, context):
    action_group = event.get("actionGroup", "")
    function = event.get("function", "")
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}

    try:
        result = analyse_drivers(
            params.get("kpi_name", "nim"),
            params.get("change_direction", "down"),
        )
    except Exception as e:
        result = {"error": str(e)}

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function,
            "functionResponse": {
                "responseBody": {"TEXT": {"body": json.dumps(result, default=str)}}
            }
        }
    }
