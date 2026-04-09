import boto3
print(boto3.__version__)
client = boto3.client('bedrock-agent', region_name='us-east-1')
print([m for m in dir(client) if 'version' in m.lower()])
