import boto3
client = boto3.client('bedrock-agent', region_name='us-east-1')
# Check all versions for supervisor
r = client.list_agent_versions(agentId='CISEMAEHAX')
for v in r['agentVersionSummaries']:
    print(v['agentVersion'], v['agentStatus'])
    detail = client.get_agent_version(agentId='CISEMAEHAX', agentVersion=v['agentVersion'])
    print('  Model:', detail['agentVersion']['foundationModel'])
