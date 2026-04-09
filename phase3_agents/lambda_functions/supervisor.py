"""
Supervisor Lambda — handles both EventBridge anomaly events
and API Gateway conversational requests. Routes to Bedrock agents.
"""
import json, os, uuid, boto3
from datetime import datetime, timezone

ssm = boto3.client("ssm")
ddb = boto3.resource("dynamodb")


def get_agent_ids() -> dict:
    """Retrieve agent IDs from SSM Parameter Store (set post-deploy)."""
    try:
        params = ssm.get_parameters(
            Names=[
                "/banking-bi/supervisor-agent-id",
                "/banking-bi/supervisor-alias-id",
            ]
        )
        result = {p["Name"].split("/")[-1]: p["Value"]
                  for p in params.get("Parameters", [])}
        return result
    except Exception:
        return {}


def invoke_bedrock_agent(agent_id: str, alias_id: str,
                          session_id: str, input_text: str) -> str:
    """Invoke a Bedrock agent and collect the full response."""
    region = os.environ.get("REGION", "us-east-1")
    bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=region)
    response = bedrock_agent_runtime.invoke_agent(
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        inputText=input_text,
    )

    completion = ""
    for event in response["completion"]:
        if "chunk" in event:
            completion += event["chunk"]["bytes"].decode("utf-8")

    return completion


def build_investigation_prompt(trigger: str, kpis: list,
                                detail: dict) -> str:
    """Build the investigation prompt for the supervisor agent."""
    kpi_list = ", ".join([k.upper() for k in kpis])
    date_str = datetime.now(timezone.utc).strftime("%d %B %Y")

    if trigger == "anomaly":
        kpi_name  = detail.get("kpi_name", "unknown").upper()
        severity  = detail.get("severity", "Medium")
        change    = detail.get("change_bps", 0)
        direction = "deteriorated" if change < 0 else "improved"
        return f"""URGENT KPI ANOMALY DETECTED — {date_str}

{kpi_name} has {direction} by {abs(change)} basis points.
Severity: {severity}

Please conduct a full investigation:
1. Retrieve current {kpi_name} data and all related KPIs: {kpi_list}
2. Analyse the drivers of this movement
3. Validate all metric calculations against governed definitions
4. Generate an executive PDF report with your findings
5. Deliver the report to the ExCo

Focus particularly on identifying whether this is a systemic issue
or isolated to specific segments/products."""

    elif trigger == "scheduled":
        return f"""DAILY KPI INVESTIGATION — {date_str}

Please conduct the daily banking performance investigation:

1. Retrieve current values for all KPIs: {kpi_list}
2. Identify any significant movements (>10 bps WoW)
3. Analyse drivers for any KPIs showing amber or red status
4. Validate all metric calculations against governed definitions
5. Generate a comprehensive executive PDF report
6. Deliver the report to the ExCo

Provide a complete picture of the bank's performance today."""

    else:
        # Conversational — use the user's message directly
        return detail.get("message", f"Please investigate all KPIs: {kpi_list}")


def handler(event, context):
    """
    Handles two trigger types:
    1. EventBridge: {"source": "banking-bi.etl", "detail-type": "KPI Anomaly Detected"}
    2. API Gateway: {"body": "{\"message\": \"...\", \"session_id\": \"...\"}"}
    3. Scheduled:   {"trigger": "scheduled", "kpis": [...]}
    """
    session_id = str(uuid.uuid4())
    kpis = ["nim", "npl_ratio", "casa_ratio",
            "roe_roa", "cost_income", "lcr_nsfr"]

    # Handle reports listing request
    path = event.get("path", "") or event.get("rawPath", "")
    if "/reports" in path or event.get("action") == "list_reports":
        s3c = boto3.client("s3", region_name=os.environ.get("REGION","us-east-1"))
        bucket = os.environ.get("OUTPUT_BUCKET","banking-bi-reports-713520983597")
        resp = s3c.list_objects_v2(Bucket=bucket, Prefix="reports/")
        files = []
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".pdf"):
                parts = key.split("/")
                name = parts[-1].replace(".pdf","").replace("-"," ").title()
                date_str = "/".join(parts[1:4]) if len(parts) >= 4 else ""
                files.append({
                    "name": name,
                    "path": key,
                    "date": obj["LastModified"].strftime("%b %d %H:%M UTC"),
                    "size": f"{obj['Size']//1024 + 1} KB",
                    "risk": "medium",
                })
        files.sort(key=lambda x: x["date"], reverse=True)
        return {
            "statusCode": 200,
            "headers": {"Content-Type":"application/json","Access-Control-Allow-Origin":"*"},
            "body": json.dumps({"reports": files}),
        }

    # Determine trigger type
    if event.get("source") == "banking-bi.etl":
        # EventBridge anomaly
        trigger = "anomaly"
        detail  = event.get("detail", {})
        kpi_name = detail.get("kpi_name")
        if kpi_name:
            kpis = [kpi_name] + [k for k in kpis if k != kpi_name]

    elif event.get("trigger") == "scheduled":
        # Scheduled EventBridge
        trigger = "scheduled"
        kpis    = event.get("kpis", kpis)
        detail  = {}

    elif event.get("httpMethod") or event.get("requestContext"):
        # API Gateway — conversational
        trigger = "conversational"
        try:
            body = json.loads(event.get("body", "{}"))
        except Exception:
            body = {}
        session_id = body.get("session_id", session_id)
        detail     = {"message": body.get("message", "Investigate all KPIs")}

    else:
        # Direct Lambda invocation
        trigger = event.get("trigger", "manual")
        kpis    = event.get("kpis", kpis)
        detail  = event.get("detail", {})

    print(f"[Supervisor] Trigger: {trigger} | Session: {session_id} | KPIs: {kpis}")

    # Build investigation prompt
    prompt = build_investigation_prompt(trigger, kpis, detail)

    # Get agent IDs from SSM
    agent_ids = get_agent_ids()
    supervisor_agent_id = agent_ids.get(
        "supervisor-agent-id",
        os.environ.get("SUPERVISOR_AGENT_ID", ""),
    )
    supervisor_alias_id = agent_ids.get(
        "supervisor-alias-id",
        os.environ.get("SUPERVISOR_ALIAS_ID", "TSTALIASID"),
    )

    if not supervisor_agent_id:
        # Agent IDs not yet configured — return instructions
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": (
                    "Agent IDs not yet configured. "
                    "Run scripts/configure_agents.py after CDK deploy."
                ),
                "session_id": session_id,
                "prompt_preview": prompt[:200],
            }),
        }

    # Invoke Bedrock supervisor agent
    try:
        print(f"[Supervisor] Invoking Bedrock agent {supervisor_agent_id}...")
        response_text = invoke_bedrock_agent(
            agent_id   = supervisor_agent_id,
            alias_id   = supervisor_alias_id,
            session_id = session_id,
            input_text = prompt,
        )
        print(f"[Supervisor] Agent response: {response_text[:200]}...")

        result = {
            "statusCode": 200,
            "session_id": session_id,
            "trigger":    trigger,
            "response":   response_text,
        }

        # Return API Gateway-compatible response for conversational trigger
        if trigger == "conversational":
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(result),
            }

        return result

    except Exception as e:
        print(f"[Supervisor] Agent invocation error: {e}")
        return {
            "statusCode": 500,
            "session_id": session_id,
            "error": str(e),
        }
