import boto3
client = boto3.client("bedrock-agent", region_name="us-east-1")
r = client.get_agent_alias(agentId="CISEMAEHAX", agentAliasId="QBTDVDFKNN")
alias = r["agentAlias"]
print("Status:", alias["agentAliasStatus"])
print("Routing:", alias["routingConfiguration"])
print("Version:", alias["routingConfiguration"][0]["agentVersion"])
