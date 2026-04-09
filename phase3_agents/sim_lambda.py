import boto3, json
# Simulate exactly what the Lambda does
import os
os.environ['REGION'] = 'us-east-1'

client = boto3.client('lambda', region_name='us-east-1')
config = client.get_function_configuration(FunctionName='banking-bi-supervisor')
env = config['Environment']['Variables']
print('SUPERVISOR_AGENT_ID:', env.get('SUPERVISOR_AGENT_ID'))
print('SUPERVISOR_ALIAS_ID:', env.get('SUPERVISOR_ALIAS_ID'))
print('REGION:', env.get('REGION'))

# Now test invoke with exact same values
bedrock = boto3.client('bedrock-agent-runtime', region_name=env.get('REGION', 'us-east-1'))
response = bedrock.invoke_agent(
    agentId=env.get('SUPERVISOR_AGENT_ID'),
    agentAliasId=env.get('SUPERVISOR_ALIAS_ID'),
    sessionId='lambda-sim-001',
    inputText='What is NIM?'
)
output = ''
for event in response['completion']:
    if 'chunk' in event:
        output += event['chunk']['bytes'].decode('utf-8')
print('Response:', output[:200])
