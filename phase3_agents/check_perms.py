import boto3, json
iam = boto3.client("iam")
policies = iam.list_role_policies(RoleName="banking-bi-agent-lambda")["PolicyNames"]
for p in policies:
    doc = iam.get_role_policy(RoleName="banking-bi-agent-lambda", PolicyName=p)["PolicyDocument"]
    for stmt in doc["Statement"]:
        actions = stmt.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        for a in actions:
            if "bedrock" in a.lower() or "agent" in a.lower():
                print(p + ": " + a + " -> " + str(stmt["Resource"]))
