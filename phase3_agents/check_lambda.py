import boto3
client = boto3.client("lambda", region_name="us-east-1")
config = client.get_function_configuration(FunctionName="banking-bi-supervisor")
print("Role:", config["Role"])
print("Agent ID env:", config["Environment"]["Variables"].get("SUPERVISOR_AGENT_ID"))
print("Alias ID env:", config["Environment"]["Variables"].get("SUPERVISOR_ALIAS_ID"))
