"""
KPI Action Lambda — handles Bedrock Agent action group invocations
for the KPI Investigation sub-agent.
"""
import json
import os
import boto3
from datetime import datetime, timezone

rds_data = boto3.client("rds-data")
bedrock  = boto3.client("bedrock-runtime", region_name=os.environ["REGION"])

RDS_SECRET_ARN = os.environ["RDS_SECRET_ARN"]
RDS_DB_NAME    = os.environ["RDS_DB_NAME"]


def get_db_arn() -> str:
    rds = boto3.client("rds")
    for db in rds.describe_db_instances()["DBInstances"]:
        if "bankingbi" in db["DBInstanceIdentifier"].lower():
            return db["DBInstanceArn"]
    raise ValueError("RDS instance not found")


def execute_sql(sql: str) -> list:
    try:
        response = rds_data.execute_statement(
            resourceArn=get_db_arn(),
            secretArn=RDS_SECRET_ARN,
            database=RDS_DB_NAME,
            sql=sql,
            formatRecordsAs="JSON",
        )
        return json.loads(response.get("formattedRecords", "[]"))
    except Exception as e:
        print(f"SQL error: {e}")
        return []


def get_kpi_data(kpi_names: str, period: str = "daily") -> dict:
    """Retrieve KPI values and trends from RDS."""
    kpis = [k.strip() for k in kpi_names.split(",")]
    results = {}

    view_map = {
        "nim":        "SELECT * FROM kpi.v_nim_latest LIMIT 10",
        "npl_ratio":  "SELECT * FROM kpi.v_npl_latest LIMIT 10",
        "casa_ratio": "SELECT * FROM kpi.v_casa_latest LIMIT 10",
        "lcr_nsfr":   "SELECT * FROM kpi.v_liquidity_latest LIMIT 10",
        "roe_roa": """
            SELECT kpi_date, bu_key, roe_pct, roa_pct,
                   roe_wow_bps, roa_wow_bps
            FROM kpi.roe_roa WHERE period_type='Daily'
            ORDER BY kpi_date DESC LIMIT 10""",
        "cost_income": """
            SELECT kpi_date, bu_key, cir_pct, cir_wow_bps,
                   total_operating_income, total_operating_expense
            FROM kpi.cost_income_ratio WHERE period_type='MTD'
            ORDER BY kpi_date DESC LIMIT 10""",
    }

    for kpi in kpis:
        sql = view_map.get(kpi)
        if sql:
            results[kpi] = execute_sql(sql)

    return results


def get_kpi_breakdown(kpi_name: str, dimension: str) -> list:
    """Get KPI breakdown by a specific dimension."""
    queries = {
        ("nim", "business_unit"): """
            SELECT b.bu_name, b.bu_type, n.nim_pct, n.nim_wow_bps
            FROM kpi.net_interest_margin n
            JOIN dim.business_unit b ON b.bu_key = n.bu_key
            WHERE n.period_type='Daily'
            ORDER BY n.kpi_date DESC, n.nim_pct DESC LIMIT 10""",
        ("npl_ratio", "product"): """
            SELECT p.product_type, p.asset_class,
                   SUM(l.outstanding_balance) as total_balance,
                   SUM(CASE WHEN l.is_npl THEN l.outstanding_balance ELSE 0 END) as npl_balance
            FROM fact.loan_position l
            JOIN dim.product p ON p.product_key = l.product_key
            GROUP BY p.product_type, p.asset_class
            ORDER BY npl_balance DESC LIMIT 10""",
        ("casa_ratio", "region"): """
            SELECT b.region, c.casa_ratio_pct, c.casa_wow_bps,
                   c.number_of_casa_accts
            FROM kpi.casa_ratio c
            JOIN dim.business_unit b ON b.bu_key = c.bu_key
            WHERE c.period_type='Daily'
            ORDER BY c.kpi_date DESC, c.casa_ratio_pct DESC LIMIT 10""",
    }

    sql = queries.get((kpi_name, dimension))
    if sql:
        return execute_sql(sql)
    return []


def handler(event, context):
    """
    Bedrock Agent action group handler.
    Parses the agent's function call and routes to the right function.
    """
    print(f"[KPI Action] Event: {json.dumps(event, default=str)[:500]}")

    action_group = event.get("actionGroup", "")
    function     = event.get("function", "")
    parameters   = {
        p["name"]: p["value"]
        for p in event.get("parameters", [])
    }

    result = {}
    try:
        if function == "get_kpi_data":
            result = get_kpi_data(
                parameters.get("kpi_names", "nim"),
                parameters.get("period", "daily"),
            )
        elif function == "get_kpi_breakdown":
            result = get_kpi_breakdown(
                parameters.get("kpi_name", "nim"),
                parameters.get("dimension", "business_unit"),
            )
        else:
            result = {"error": f"Unknown function: {function}"}
    except Exception as e:
        result = {"error": str(e)}

    # Bedrock agent action group response format
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": json.dumps(result, default=str)
                    }
                }
            }
        }
    }
