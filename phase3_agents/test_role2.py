import boto3, json, time

time.sleep(5)  # Wait for trust policy propagation

sts = boto3.client('sts')
role = sts.assume_role(
    RoleArn='arn:aws:iam::713520983597:role/banking-bi-agent-lambda',
    RoleSessionName='debug-session'
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
        sessionId='role-test-002',
        inputText='What is NIM?'
    )
    output = ''
    for event in response['completion']:
        if 'chunk' in event:
            output += event['chunk']['bytes'].decode('utf-8')
    print('SUCCESS:', output[:200])
except Exception as e:
    print('ERROR:', str(e))
