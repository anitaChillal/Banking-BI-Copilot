import sys
sys.path.insert(0, "/opt/python")
import json, os, io, uuid, boto3
from datetime import datetime, timezone

s3_client  = boto3.client("s3")
sns_client = boto3.client("sns")
bedrock    = boto3.client("bedrock-runtime", region_name=os.environ.get("REGION", "us-east-1"))
ddb        = boto3.resource("dynamodb")
MODEL_ID      = os.environ.get("MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET", "banking-bi-reports-713520983597")
SUMMARY_TOPIC = os.environ.get("SUMMARY_TOPIC_ARN", "")
SESSION_TABLE = os.environ.get("SESSION_TABLE", "banking-bi-agent-sessions")

def generate_narrative(findings_json, headline):
    prompt = (
        "You are a Chief Analytics Officer preparing a banking performance report.\n\n"
        "HEADLINE: " + headline + "\n\n"
        "FINDINGS: " + str(findings_json)[:2000] + "\n\n"
        "Write an executive report with sections:\n"
        "## EXECUTIVE SUMMARY\n## KPI PERFORMANCE DASHBOARD\n"
        "## KEY FINDINGS\n## ROOT CAUSE ANALYSIS\n"
        "## REGULATORY POSITION\n## MANAGEMENT ACTIONS REQUIRED\n\n"
        "Use precise banking language. Maximum 500 words."
    )
    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
            }),
        )
        return json.loads(response["body"].read())["content"][0]["text"].strip()
    except Exception as e:
        print("[PDF] Narrative error:", e)
        return "Executive summary unavailable."

def build_pdf(session_id, headline, risk_level, narrative, report_date):
    print("[PDF] Importing reportlab...")
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER
    print("[PDF] reportlab imported OK")
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    navy = HexColor("#0A2342")
    gray = HexColor("#F5F5F5")
    risk_colors = {"low": HexColor("#417505"), "medium": HexColor("#F5A623"),
                   "high": HexColor("#D0021B"), "critical": HexColor("#D0021B")}
    risk_color = risk_colors.get(risk_level.lower(), HexColor("#F5A623"))
    title_s = ParagraphStyle("T", parent=styles["Normal"], fontSize=18, textColor=white, fontName="Helvetica-Bold")
    section_s = ParagraphStyle("S", parent=styles["Normal"], fontSize=13, textColor=navy, fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=6)
    body_s = ParagraphStyle("B", parent=styles["Normal"], fontSize=10, textColor=black, fontName="Helvetica", spaceAfter=8, leading=15)
    sub_s = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=HexColor("#CCE0FF"))
    story = []
    ht = Table([[Paragraph("APEX BANK — BI COPILOT", title_s), Paragraph("CONFIDENTIAL | " + report_date, sub_s)]], colWidths=[12*cm, 5*cm])
    ht.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),navy),("PADDING",(0,0),(-1,-1),12),("ALIGN",(1,0),(1,0),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    story.append(ht)
    story.append(Spacer(1, 0.3*cm))
    rt = Table([[Paragraph("RISK LEVEL: " + risk_level.upper(), ParagraphStyle("r", parent=styles["Normal"], fontSize=11, textColor=white, fontName="Helvetica-Bold"))]], colWidths=[17*cm])
    rt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),risk_color),("PADDING",(0,0),(-1,-1),8)]))
    story.append(rt)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("<b>Key Finding:</b> " + headline, ParagraphStyle("hf", parent=styles["Normal"], fontSize=11, textColor=navy, backColor=gray, borderPad=8, spaceAfter=12)))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#DDDDDD")))
    story.append(Spacer(1, 0.2*cm))
    for line in narrative.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.1*cm))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], section_s))
        elif line.startswith("- ") or line.startswith("* "):
            story.append(Paragraph("&bull; " + line[2:], ParagraphStyle("bl", parent=body_s, leftIndent=12)))
        else:
            story.append(Paragraph(line, body_s))
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#DDDDDD")))
    story.append(Paragraph("CONFIDENTIAL — Internal use only. Session: " + session_id, ParagraphStyle("ft", parent=styles["Normal"], fontSize=8, textColor=HexColor("#888888"), alignment=TA_CENTER)))
    doc.build(story)
    size = len(buffer.getvalue())
    print("[PDF] Built successfully, size:", size, "bytes")
    return buffer.getvalue()

def generate_pdf_report(session_id, headline, findings_json, risk_level):
    report_date = datetime.now(timezone.utc).strftime("%d %B %Y")
    date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    narrative = generate_narrative(findings_json, headline)
    try:
        pdf_bytes = build_pdf(session_id, headline, risk_level, narrative, report_date)
        content_type = "application/pdf"
    except Exception as e:
        print("[PDF] build_pdf failed:", e)
        import traceback; traceback.print_exc()
        pdf_bytes = narrative.encode("utf-8")
        content_type = "text/plain"
    report_name = "kpi-investigation-" + today
    pdf_key = "reports/" + date_prefix + "/" + report_name + ".pdf"
    txt_key = "reports/" + date_prefix + "/" + report_name + "_narrative.txt"
    s3_client.put_object(Bucket=OUTPUT_BUCKET, Key=pdf_key, Body=pdf_bytes, ContentType=content_type)
    s3_client.put_object(Bucket=OUTPUT_BUCKET, Key=txt_key, Body=narrative.encode("utf-8"), ContentType="text/plain")
    try:
        ddb.Table(SESSION_TABLE).put_item(Item={
            "session_id": session_id, "timestamp": datetime.now(timezone.utc).isoformat(),
            "headline": headline, "risk_level": risk_level, "pdf_key": pdf_key,
            "ttl": int(datetime.now(timezone.utc).timestamp()) + (90 * 86400),
        })
    except Exception as e:
        print("[PDF] DynamoDB error:", e)
    s3_path = "s3://" + OUTPUT_BUCKET + "/" + pdf_key
    print("[PDF Action] Report saved:", s3_path)
    return {"session_id": session_id, "pdf_s3_path": s3_path, "pdf_key": pdf_key,
            "report_date": report_date, "status": "generated", "content_type": content_type}

def deliver_report(session_id, recipient_group="exco"):
    try:
        import boto3.dynamodb.conditions as cond
        result = ddb.Table(SESSION_TABLE).query(
            KeyConditionExpression=cond.Key("session_id").eq(session_id), Limit=1, ScanIndexForward=False)
        items = result.get("Items", [])
        if not items:
            return {"error": "Session not found"}
        item = items[0]
        pdf_key = item.get("pdf_key", "")
        headline = item.get("headline", "KPI Report")
        risk = item.get("risk_level", "medium")
        try:
            presigned = s3_client.generate_presigned_url("get_object",
                Params={"Bucket": OUTPUT_BUCKET, "Key": pdf_key}, ExpiresIn=86400)
        except Exception:
            presigned = "s3://" + OUTPUT_BUCKET + "/" + pdf_key
        if SUMMARY_TOPIC:
            sns_client.publish(TopicArn=SUMMARY_TOPIC,
                Subject=("[Banking BI] " + headline)[:100],
                Message="Banking BI Report\n\n" + headline + "\nRisk: " + risk + "\n" + presigned)
        return {"session_id": session_id, "delivered_to": recipient_group, "presigned_url": presigned, "status": "delivered"}
    except Exception as e:
        return {"error": str(e)}

def handler(event, context):
    action_group = event.get("actionGroup", "")
    function = event.get("function", "")
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}
    print("[PDF Action] function:", function)
    try:
        if function == "generate_pdf_report":
            result = generate_pdf_report(
                params.get("session_id", str(uuid.uuid4())),
                params.get("headline", "KPI investigation complete"),
                params.get("findings_json", "{}"),
                params.get("risk_level", "medium"),
            )
        elif function == "deliver_report":
            result = deliver_report(params.get("session_id"), params.get("recipient_group", "exco"))
        else:
            result = {"error": "Unknown function: " + function}
    except Exception as e:
        import traceback; traceback.print_exc()
        result = {"error": str(e)}
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function,
            "functionResponse": {"responseBody": {"TEXT": {"body": json.dumps(result, default=str)}}}
        }
    }
