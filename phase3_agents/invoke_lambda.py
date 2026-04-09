import boto3, json

client = boto3.client('lambda', region_name='us-east-1')

# Invoke with a debug payload
response = client.invoke(
    FunctionName='banking-bi-supervisor',
    InvocationType='RequestResponse',
    Payload=json.dumps({'trigger': 'debug', 'kpis': ['nim']}).encode()
)
result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2, default=str))
