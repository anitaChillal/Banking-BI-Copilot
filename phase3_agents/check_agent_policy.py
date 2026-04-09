import boto3, json
client = boto3.client('bedrock-agent', region_name='us-east-1')

# Check if agent has resource policy
try:
    r = client.get_agent(agentId='CISEMAEHAX')
    print(json.dumps(r['agent'], indent=2, default=str))
except Exception as e:
    print('Error:', e)
