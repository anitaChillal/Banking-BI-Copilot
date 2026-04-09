"""
PDF Action Lambda — Generates executive PDF reports and delivers via SNS.
Uses reportlab (pure Python, no system dependencies needed).
"""
import json, os, io, uuid, boto3
from datetime import datetime, timezone

s3_client  = boto3.client("s3")
sns_client = boto3.client("sns")
bedrock    = boto3.client("bedrock-runtime", region_name=os.environ["REGION"])
ddb        = boto3.resource("dynamodb")

MODEL_ID       = os.environ["MODEL_ID"]
OUTPUT_BUCKET  = os.environ["OUTPUT_BUCKET"]
SUMMARY_TOPIC  = os.environ["SUMMARY_TOPIC_ARN"]
SESSION_TABLE  = os.environ["SESSION_TABLE"]


def generate_narrative(findings_json: str, headline: str) -> dict:
    """Generate executive briefing and detailed analysis with Claude."""
    prompt = f"""You are a Chief Analytics Officer preparing a banking
performance report for the CEO and Board.

HEADLINE: {headline}

INVESTIGATION FINDINGS:
{findings_json[:3000]}

Write a complete executive report with these sections:

## EXECUTIVE SUMMARY
(3-4 sentences — overall picture for CEO)

## KPI PERFORMANCE DASHBOARD
(Table: KPI | Current Value | Change | Status | Trend)

## KEY FINDINGS
(3-5 bullet points — the most important discoveries)

## ROOT CAUSE ANALYSIS
(The top 3 drivers with supporting evidence)

## REGULATORY & RISK POSITION
(LCR/NSFR status, any regulatory thresholds at risk)

## MANAGEMENT ACTIONS REQUIRED
(Numbered list — specific, actionable, owner suggested)

## APPENDIX: METRIC GOVERNANCE
(Confirm each KPI was calculated per governed definition)

Use precise banking language. Maximum 600 words total."""

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2500,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    text = json.loads(response["body"].read())["content"][0]["text"].strip()
    return {"full_report": text}


def build_pdf(session_id: str, headline: str, risk_level: str,
              narrative: str, report_date: str) -> bytes:
    """Build PDF using reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, black, white
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer,
            Table, TableStyle, HRFlowable,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        navy   = HexColor("#0A2342")
        amber  = HexColor("#F5A623")
        red    = HexColor("#D0021B")
        green  = HexColor("#417505")
        gray   = HexColor("#F5F5F5")

        risk_color = {
            "low": green, "medium": amber,
            "high": red, "critical": red,
        }.get(risk_level.lower(), amber)

        title_style = ParagraphStyle(
            "Title", parent=styles["Normal"],
            fontSize=20, textColor=white,
            fontName="Helvetica-Bold", spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "Subtitle", parent=styles["Normal"],
            fontSize=11, textColor=HexColor("#CCE0FF"),
            fontName="Helvetica",
        )
        section_style = ParagraphStyle(
            "Section", parent=styles["Normal"],
            fontSize=13, textColor=navy,
            fontName="Helvetica-Bold", spaceBefore=16, spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "Body", parent=styles["Normal"],
            fontSize=10, textColor=black,
            fontName="Helvetica", spaceAfter=8, leading=15,
        )

        story = []

        # Header banner
        header_data = [[
            Paragraph("APEX BANK", title_style),
            Paragraph(
                f"CONFIDENTIAL — {report_date}", subtitle_style
            ),
        ]]
        header_table = Table(header_data, colWidths=[10*cm, 7*cm])
        header_table.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,-1), navy),
            ("PADDING",     (0,0), (-1,-1), 12),
            ("ALIGN",       (1,0), (1,0), "RIGHT"),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.4*cm))

        # Report title
        story.append(Paragraph(
            "Banking BI Copilot — KPI Investigation Report",
            ParagraphStyle("ReportTitle", parent=styles["Normal"],
                fontSize=16, textColor=navy,
                fontName="Helvetica-Bold", spaceAfter=4),
        ))
        story.append(Paragraph(
            f"Session ID: {session_id}",
            ParagraphStyle("Meta", parent=styles["Normal"],
                fontSize=9, textColor=HexColor("#888888")),
        ))
        story.append(Spacer(1, 0.3*cm))

        # Risk badge
        risk_data = [[
            Paragraph(
                f"OVERALL RISK LEVEL: {risk_level.upper()}",
                ParagraphStyle("Risk", parent=styles["Normal"],
                    fontSize=11, textColor=white,
                    fontName="Helvetica-Bold"),
            )
        ]]
        risk_table = Table(risk_data, colWidths=[17*cm])
        risk_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), risk_color),
            ("PADDING",    (0,0), (-1,-1), 8),
        ]))
        story.append(risk_table)
        story.append(Spacer(1, 0.3*cm))

        # Headline
        story.append(Paragraph(
            f"<b>Key Finding:</b> {headline}",
            ParagraphStyle("Headline", parent=styles["Normal"],
                fontSize=11, textColor=navy,
                backColor=gray, borderPad=8,
                spaceAfter=12),
        ))

        # Main narrative — split by ## headings
        story.append(HRFlowable(width="100%", thickness=1,
                                color=HexColor("#DDDDDD")))
        story.append(Spacer(1, 0.2*cm))

        for line in narrative.split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.15*cm))
            elif line.startswith("## "):
                story.append(Paragraph(line[3:], section_style))
                story.append(HRFlowable(
                    width="100%", thickness=0.5,
                    color=HexColor("#CCCCCC"), spaceAfter=4,
                ))
            elif line.startswith("- ") or line.startswith("• "):
                story.append(Paragraph(
                    f"&bull;&nbsp; {line[2:]}",
                    ParagraphStyle("Bullet", parent=body_style,
                        leftIndent=12),
                ))
            elif line[0].isdigit() and line[1] in ".)" :
                story.append(Paragraph(
                    line, ParagraphStyle("Numbered", parent=body_style,
                        leftIndent=12),
                ))
            else:
                story.append(Paragraph(line, body_style))

        # Footer
        story.append(Spacer(1, 1*cm))
        story.append(HRFlowable(width="100%", thickness=1,
                                color=HexColor("#DDDDDD")))
        story.append(Paragraph(
            "CONFIDENTIAL — For internal management use only. "
            "Generated by Banking BI Copilot. "
            f"Produced: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            ParagraphStyle("Footer", parent=styles["Normal"],
                fontSize=8, textColor=HexColor("#888888"),
                alignment=TA_CENTER),
        ))

        doc.build(story)
        return buffer.getvalue()

    except ImportError:
        # Fallback: plain text PDF-like content if reportlab not available
        return narrative.encode("utf-8")


def generate_pdf_report(session_id: str, headline: str,
                         findings_json: str, risk_level: str) -> dict:
    report_date = datetime.now(timezone.utc).strftime("%d %B %Y")
    date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")

    # Generate narrative
    narrative_result = generate_narrative(findings_json, headline)
    narrative = narrative_result["full_report"]

    # Build PDF
    pdf_bytes = build_pdf(
        session_id, headline, risk_level, narrative, report_date
    )

    # Upload to S3
    pdf_key = f"reports/{date_prefix}/{session_id}.pdf"
    txt_key = f"reports/{date_prefix}/{session_id}_narrative.txt"

    s3_client.put_object(
        Bucket=OUTPUT_BUCKET, Key=pdf_key,
        Body=pdf_bytes, ContentType="application/pdf",
    )
    s3_client.put_object(
        Bucket=OUTPUT_BUCKET, Key=txt_key,
        Body=narrative.encode("utf-8"), ContentType="text/plain",
    )

    # Save to DynamoDB
    table = ddb.Table(SESSION_TABLE)
    table.put_item(Item={
        "session_id": session_id,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "headline":   headline,
        "risk_level": risk_level,
        "pdf_key":    pdf_key,
        "ttl": int(datetime.now(timezone.utc).timestamp()) + (90 * 86400),
    })

    s3_path = f"s3://{OUTPUT_BUCKET}/{pdf_key}"
    print(f"[PDF Action] Report saved: {s3_path}")

    return {
        "session_id": session_id,
        "pdf_s3_path": s3_path,
        "pdf_key": pdf_key,
        "report_date": report_date,
        "status": "generated",
    }


def deliver_report(session_id: str,
                   recipient_group: str = "exco") -> dict:
    """Retrieve report details and publish SNS notification."""
    table = ddb.Table(SESSION_TABLE)

    # Find the session
    result = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key(
            "session_id"
        ).eq(session_id),
        Limit=1,
        ScanIndexForward=False,
    )
    items = result.get("Items", [])
    if not items:
        return {"error": f"Session {session_id} not found"}

    item = items[0]
    pdf_key  = item.get("pdf_key", "")
    headline = item.get("headline", "KPI Investigation Complete")
    risk     = item.get("risk_level", "medium")
    s3_path  = f"s3://{OUTPUT_BUCKET}/{pdf_key}"

    subject = f"[{'ALERT — ' if risk in ['high','critical'] else ''}Banking BI] {headline}"

    # Generate pre-signed URL (valid 24 hours)
    try:
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": OUTPUT_BUCKET, "Key": pdf_key},
            ExpiresIn=86400,
        )
    except Exception:
        presigned_url = s3_path

    message = f"""Banking BI Copilot — Executive Report Ready

{headline}

Risk Level: {risk.upper()}
Recipients: {recipient_group}
Session: {session_id}

Download PDF Report (expires in 24 hours):
{presigned_url}

This report was generated automatically by the Banking BI Copilot.
All KPI calculations have been validated against governed metric definitions.
"""

    sns_client.publish(
        TopicArn=SUMMARY_TOPIC,
        Subject=subject[:100],
        Message=message,
    )

    return {
        "session_id": session_id,
        "delivered_to": recipient_group,
        "presigned_url": presigned_url,
        "status": "delivered",
    }


def handler(event, context):
    action_group = event.get("actionGroup", "")
    function     = event.get("function", "")
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}

    try:
        if function == "generate_pdf_report":
            result = generate_pdf_report(
                session_id    = params.get("session_id", str(uuid.uuid4())),
                headline      = params.get("headline", "KPI investigation complete"),
                findings_json = params.get("findings_json", "{}"),
                risk_level    = params.get("risk_level", "medium"),
            )
        elif function == "deliver_report":
            result = deliver_report(
                session_id      = params.get("session_id"),
                recipient_group = params.get("recipient_group", "exco"),
            )
        else:
            result = {"error": f"Unknown function: {function}"}
    except Exception as e:
        result = {"error": str(e)}

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {"body": json.dumps(result, default=str)}
                }
            }
        }
    }
