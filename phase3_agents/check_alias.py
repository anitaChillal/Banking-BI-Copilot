import boto3
client = boto3.client('bedrock-agent', region_name='us-east-1')
r = client.get_agent_alias(agentId='CISEMAEHAX', agentAliasId='QBTDVDFKNN')
print(r['agentAlias']['agentAliasStatus'])
print(r['agentAlias']['routingConfiguration'])
