import boto3, json
iam = boto3.client('iam')
policies = iam.list_role_policies(RoleName='banking-bi-agent-lambda')['PolicyNames']
print('Policies:', policies)
for p in policies:
    doc = iam.get_role_policy(RoleName='banking-bi-agent-lambda', PolicyName=p)['PolicyDocument']
    print(p + ':', json.dumps(doc, indent=2))
