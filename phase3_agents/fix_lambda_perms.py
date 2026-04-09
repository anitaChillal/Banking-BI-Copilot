import boto3, json
iam = boto3.client('iam')
policy = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Effect': 'Allow',
            'Action': ['bedrock:InvokeAgent'],
            'Resource': [
                'arn:aws:bedrock:us-east-1:713520983597:agent/CISEMAEHAX',
                'arn:aws:bedrock:us-east-1:713520983597:agent-alias/CISEMAEHAX/QBTDVDFKNN',
                'arn:aws:bedrock:us-east-1:713520983597:agent/*',
                'arn:aws:bedrock:us-east-1:713520983597:agent-alias/*/*'
            ]
        },
        {
            'Effect': 'Allow',
            'Action': ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
            'Resource': '*'
        }
    ]
}
iam.put_role_policy(
    RoleName='banking-bi-agent-lambda',
    PolicyName='BedrockAgentInvokePolicy',
    PolicyDocument=json.dumps(policy)
)
print('Done')
