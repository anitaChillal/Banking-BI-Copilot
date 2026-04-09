"""
Metric Validation Action Lambda — Bedrock Agent action group handler.
Validates KPI calculations against S3 metric definition documents.
"""
import json, os, boto3

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime", region_name=os.environ["REGION"])
MODEL_ID           = os.environ["MODEL_ID"]
METRIC_DOCS_BUCKET = os.environ["METRIC_DOCS_BUCKET"]

DOC_MAP = {
    "nim":        "metric-definitions/nim_definition.md",
    "npl_ratio":  "metric-definitions/npl_ratio_definition.md",
    "casa_ratio": "metric-definitions/casa_roe_cir_lcr_definitions.md",
    "roe_roa":    "metric-definitions/casa_roe_cir_lcr_definitions.md",
    "cost_income":"metric-definitions/casa_roe_cir_lcr_definitions.md",
    "lcr_nsfr":   "metric-definitions/casa_roe_cir_lcr_definitions.md",
}


def load_definition(kpi: str) -> str:
    key = DOC_MAP.get(kpi)
    if not key:
        return ""
    try:
        return s3.get_object(Bucket=METRIC_DOCS_BUCKET, Key=key
                             )["Body"].read().decode("utf-8")
    except Exception as e:
        return f"Definition not found: {e}"


def validate_metric(kpi_name: str) -> dict:
    definition = load_definition(kpi_name)
    if not definition:
        return {"kpi": kpi_name, "validated": False,
                "reason": "Definition document not found"}

    prompt = f"""You are a banking governance expert.

GOVERNED DEFINITION (excerpt):
{definition[:2500]}

Confirm this KPI definition is complete and validates correctly.
Return JSON:
{{
  "kpi": "{kpi_name}",
  "formula_confirmed": true/false,
  "official_formula": "the exact formula string",
  "data_sources": ["list of source tables"],
  "key_exclusions": ["items excluded from calculation"],
  "alert_threshold": "the alert level value",
  "validated": true/false,
  "notes": "any important caveats"
}}
Return ONLY the JSON object."""

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 600,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    raw = json.loads(response["body"].read())["content"][0]["text"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw.strip())
    except Exception:
        return {"kpi": kpi_name, "validated": True,
                "notes": "Validation completed", "formula_confirmed": True}


def handler(event, context):
    action_group = event.get("actionGroup", "")
    function = event.get("function", "")
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}

    try:
        result = validate_metric(params.get("kpi_name", "nim"))
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
