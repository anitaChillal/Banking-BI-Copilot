import boto3, json

# Test with assumed role credentials (simulate Lambda)
sts = boto3.client('sts')
role = sts.assume_role(
    RoleArn='arn:aws:iam::713520983597:role/banking-bi-agent-lambda',
    RoleSessionName='test-session'
)
creds = role['Credentials']

client = boto3.client(
    'bedrock-agent-runtime',
    region_name='us-east-1',
    aws_access_key_id=creds['AccessKeyId'],
    aws_secret_access_key=creds['SecretAccessKey'],
    aws_session_token=creds['SessionToken']
)

try:
    response = client.invoke_agent(
        agentId='CISEMAEHAX',
        agentAliasId='QBTDVDFKNN',
        sessionId='role-test-001',
        inputText='What is NIM?'
    )
    output = ''
    for event in response['completion']:
        if 'chunk' in event:
            output += event['chunk']['bytes'].decode('utf-8')
    print('SUCCESS:', output[:200])
except Exception as e:
    print('ERROR:', str(e))
