import boto3, json

# Simulate Lambda exactly
agent_id = 'CISEMAEHAX'
alias_id = 'QBTDVDFKNN'
session_id = 'lambda-exact-sim'

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
try:
    response = client.invoke_agent(
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        inputText='Daily KPI investigation for NIM, NPL'
    )
    output = ''
    for event in response['completion']:
        if 'chunk' in event:
            output += event['chunk']['bytes'].decode('utf-8')
    print('SUCCESS:', output[:300])
except Exception as e:
    print('ERROR:', str(e))
