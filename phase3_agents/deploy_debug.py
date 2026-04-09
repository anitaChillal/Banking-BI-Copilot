import boto3, json, zipfile, io

client = boto3.client("lambda", region_name="us-east-1")

debug_code = """
import boto3, os, json

def handler(event, context):
    region = os.environ.get("REGION", "us-east-1")
    agent_id = os.environ.get("SUPERVISOR_AGENT_ID")
    alias_id = os.environ.get("SUPERVISOR_ALIAS_ID")
    print("Region: " + str(region))
    print("Agent ID: " + str(agent_id))
    print("Alias ID: " + str(alias_id))
    sts = boto3.client("sts")
    identity = sts.get_caller_identity()
    print("Caller ARN: " + identity["Arn"])
    bedrock = boto3.client("bedrock-agent-runtime", region_name=region)
    try:
        response = bedrock.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId="debug-001",
            inputText="What is NIM?"
        )
        output = ""
        for ev in response["completion"]:
            if "chunk" in ev:
                output += ev["chunk"]["bytes"].decode("utf-8")
        return {"status": "success", "response": output[:200]}
    except Exception as e:
        return {"status": "error", "error": str(e)}
"""

buffer = io.BytesIO()
with zipfile.ZipFile(buffer, "w") as z:
    z.writestr("supervisor.py", debug_code)
buffer.seek(0)

client.update_function_code(
    FunctionName="banking-bi-supervisor",
    ZipFile=buffer.read()
)
print("Deployed")
