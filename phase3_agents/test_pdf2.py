import boto3, json, time
client = boto3.client("lambda", region_name="us-east-1")
payload = {
    "actionGroup": "pdf-report-actions",
    "function": "generate_pdf_report",
    "parameters": [
        {"name":"session_id","value":"test-pdf-002"},
        {"name":"headline","value":"Test PDF with reportlab"},
        {"name":"findings_json","value":"{}"},
        {"name":"risk_level","value":"low"},
    ]
}
response = client.invoke(
    FunctionName="banking-bi-pdf-action",
    InvocationType="RequestResponse",
    Payload=json.dumps(payload).encode()
)
result = json.loads(response["Payload"].read())
body = json.loads(result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
print("PDF path:", body.get("pdf_s3_path"))
print("Status:", body.get("status"))
