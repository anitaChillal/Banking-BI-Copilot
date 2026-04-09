import boto3
client = boto3.client('bedrock-agent', region_name='us-east-1')
agents = [
    ('CISEMAEHAX', 'supervisor'),
    ('ORFQX7RUGT', 'kpi-investigation'),
    ('VKM5M6TZGD', 'driver-analysis'),
    ('YNN2V3LD01', 'metric-validation'),
]
for agent_id, name in agents:
    aliases = client.list_agent_aliases(agentId=agent_id)['agentAliasSummaries']
    for a in aliases:
        if a['agentAliasId'] != 'TSTALIASID':
            print(name + ': ' + a['agentAliasId'] + ' -> version ' + str(a.get('routingConfiguration', [{}])[0].get('agentVersion', '?')))
