import boto3, json
client = boto3.client("lambda", region_name="us-east-1")

# Test if reportlab actually works in the Lambda
test_code = """
import boto3, json, io

def handler(event, context):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        styles = getSampleStyleSheet()
        doc.build([Paragraph("Test PDF", styles["Title"])])
        size = len(buf.getvalue())
        return {"status": "ok", "size": size, "first_bytes": buf.getvalue()[:4].decode("latin-1")}
    except Exception as e:
        return {"status": "error", "error": str(e)}
"""

import zipfile, io as sysio
buffer = sysio.BytesIO()
with zipfile.ZipFile(buffer, "w") as z:
    z.writestr("lambda_function.py", test_code)
buffer.seek(0)

client.update_function_code(FunctionName="banking-bi-pdf-action", ZipFile=buffer.read())
import time; time.sleep(5)

response = client.invoke(
    FunctionName="banking-bi-pdf-action",
    InvocationType="RequestResponse",
    Payload=json.dumps({}).encode()
)
print(json.loads(response["Payload"].read()))
