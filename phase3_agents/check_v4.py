import boto3
client = boto3.client('bedrock-agent', region_name='us-east-1')
r = client.get_agent_version(agentId='CISEMAEHAX', agentVersion='4')
print(r['agentVersion']['foundationModel'])
print(r['agentVersion']['agentStatus'])
