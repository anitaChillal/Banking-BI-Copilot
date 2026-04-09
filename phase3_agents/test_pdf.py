import boto3, json
client = boto3.client("lambda", region_name="us-east-1")
payload = {
    "actionGroup": "pdf-report-actions",
    "function": "generate_pdf_report",
    "parameters": [
        {"name":"session_id","value":"test-pdf-001"},
        {"name":"headline","value":"NIM compressed 18 bps — funding cost pressure identified"},
        {"name":"findings_json","value":"{}"},
        {"name":"risk_level","value":"high"},
    ]
}
response = client.invoke(
    FunctionName="banking-bi-pdf-action",
    InvocationType="RequestResponse",
    Payload=json.dumps(payload).encode()
)
result = json.loads(response["Payload"].read())
print(json.dumps(result, indent=2))
