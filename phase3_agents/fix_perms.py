import boto3, json
iam = boto3.client('iam')

# Check current policies on lambda role
policies = iam.list_role_policies(RoleName='banking-bi-agent-lambda')['PolicyNames']
print('Policies:', policies)

# Add bedrock-agent-runtime permission explicitly
policy = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Effect': 'Allow',
            'Action': [
                'bedrock:InvokeAgent',
                'bedrock-agent-runtime:InvokeAgent',
                'bedrock:InvokeModel',
                'bedrock:InvokeModelWithResponseStream'
            ],
            'Resource': '*'
        }
    ]
}
iam.put_role_policy(
    RoleName='banking-bi-agent-lambda',
    PolicyName='BedrockRuntimeAccess',
    PolicyDocument=json.dumps(policy)
)
print('Policy updated')
