import boto3
client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
response = client.invoke_agent(
    agentId='CISEMAEHAX',
    agentAliasId='QBTDVDFKNN',
    sessionId='direct-test-001',
    inputText='What is NIM?'
)
output = ''
for event in response['completion']:
    if 'chunk' in event:
        output += event['chunk']['bytes'].decode('utf-8')
print(output[:300])
