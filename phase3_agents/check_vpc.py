import boto3
client = boto3.client('lambda', region_name='us-east-1')
config = client.get_function_configuration(FunctionName='banking-bi-supervisor')
vpc = config.get('VpcConfig', {})
print('VPC ID:', vpc.get('VpcId', 'None - not in VPC'))
print('Subnets:', vpc.get('SubnetIds', []))
