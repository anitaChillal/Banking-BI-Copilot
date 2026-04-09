import boto3, json, time
client = boto3.client("lambda", region_name="us-east-1")
payload = {
    "actionGroup": "pdf-report-actions",
    "function": "generate_pdf_report",
    "parameters": [
        {"name":"session_id","value":"test-pdf-003"},
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
print(json.dumps(result, indent=2, default=str))
