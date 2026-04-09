import boto3, zipfile, io, os

# Write the new pdf_action.py content
new_code = open(r"C:\Users\anita\banking-bi-copilot\phase3_agents\lambda_functions\pdf_action.py").read()
print("File starts with:", new_code[:100])
print("Has reportlab check:", "Importing reportlab" in new_code)
print("Has today fix:", "today = datetime" in new_code)
