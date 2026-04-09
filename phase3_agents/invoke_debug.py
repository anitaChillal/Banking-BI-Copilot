import boto3, json, time
time.sleep(5)
client = boto3.client("lambda", region_name="us-east-1")
response = client.invoke(
    FunctionName="banking-bi-supervisor",
    InvocationType="RequestResponse",
    Payload=json.dumps({}).encode()
)
result = json.loads(response["Payload"].read())
print(json.dumps(result, indent=2))
