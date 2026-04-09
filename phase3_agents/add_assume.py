import boto3, json
iam = boto3.client('iam')
policy = {
    'Version': '2012-10-17',
    'Statement': [{
        'Effect': 'Allow',
        'Action': 'sts:AssumeRole',
        'Resource': 'arn:aws:iam::713520983597:role/banking-bi-agent-lambda'
    }]
}
iam.put_user_policy(
    UserName='cdk-deployer',
    PolicyName='AssumeRolePolicy',
    PolicyDocument=json.dumps(policy)
)
print('Done')
