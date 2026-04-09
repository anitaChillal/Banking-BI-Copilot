import boto3
client = boto3.client('bedrock-agent', region_name='us-east-1')
agents = ['CISEMAEHAX','ORFQX7RUGT','VKM5M6TZGD','YNN2V3LD01']
for aid in agents:
    r = client.get_agent(agentId=aid)['agent']
    print(r['agentName'], r['foundationModel'], r['agentStatus'])
