import boto3, time
client = boto3.client('bedrock-agent', region_name='us-east-1')
agents = ['CISEMAEHAX','ORFQX7RUGT','VKM5M6TZGD','YNN2V3LD01']
for agent_id in agents:
    aliases = client.list_agent_aliases(agentId=agent_id)['agentAliasSummaries']
    for alias in aliases:
        if alias['agentAliasId'] != 'TSTALIASID':
            client.delete_agent_alias(agentId=agent_id, agentAliasId=alias['agentAliasId'])
            print('Deleted alias ' + alias['agentAliasId'] + ' from ' + agent_id)
            time.sleep(2)
