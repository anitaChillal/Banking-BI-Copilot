import boto3, time
client = boto3.client('bedrock-agent', region_name='us-east-1')
agents = ['CISEMAEHAX','ORFQX7RUGT','VKM5M6TZGD','YNN2V3LD01']
for agent_id in agents:
    versions = client.list_agent_versions(agentId=agent_id)['agentVersionSummaries']
    for v in versions:
        if v['agentVersion'] != 'DRAFT':
            client.delete_agent_version(agentId=agent_id, agentVersion=v['agentVersion'])
            print('Deleted version ' + v['agentVersion'] + ' from ' + agent_id)
            time.sleep(2)
