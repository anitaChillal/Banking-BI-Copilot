import boto3, time
client = boto3.client('bedrock-agent', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

agents = [
    ('CISEMAEHAX', 'banking-bi-supervisor'),
    ('ORFQX7RUGT', 'banking-bi-kpi-investigation'),
    ('VKM5M6TZGD', 'banking-bi-driver-analysis'),
    ('YNN2V3LD01', 'banking-bi-metric-validation'),
]

alias_ids = {}
for agent_id, name in agents:
    # Create a new version from the prepared DRAFT
    version_r = client.create_agent_version(agentId=agent_id)
    version = version_r['agentVersion']['agentVersion']
    print(name + ': created version ' + str(version))
    time.sleep(5)

    # Create alias pointing to this version
    alias_r = client.create_agent_alias(
        agentId=agent_id,
        agentAliasName='live-haiku',
        routingConfiguration=[{'agentVersion': str(version)}],
    )
    alias_id = alias_r['agentAlias']['agentAliasId']
    alias_ids[agent_id] = alias_id
    print(name + ': alias ' + alias_id)
    time.sleep(2)

config = lambda_client.get_function_configuration(FunctionName='banking-bi-supervisor')
env = config['Environment']['Variables']
supervisor_alias = alias_ids['CISEMAEHAX']
env['SUPERVISOR_ALIAS_ID'] = supervisor_alias
lambda_client.update_function_configuration(
    FunctionName='banking-bi-supervisor',
    Environment={'Variables': env}
)
print('Lambda updated with alias ' + supervisor_alias)
