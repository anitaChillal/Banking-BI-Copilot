import boto3
client = boto3.client('lambda', region_name='us-east-1')
config = client.get_function_configuration(FunctionName='banking-bi-supervisor')
env = config['Environment']['Variables']
env['SUPERVISOR_ALIAS_ID'] = 'QBTDVDFKNN'
client.update_function_configuration(FunctionName='banking-bi-supervisor', Environment={'Variables': env})
print('Done')
