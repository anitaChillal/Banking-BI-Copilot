#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.knowledge_base_stack import KnowledgeBaseStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1",
)

kb_stack = KnowledgeBaseStack(app, "BankingBIKnowledgeBase",
    env=env,
    description="Phase 2 — Bedrock Knowledge Base + OpenSearch Serverless",
)

cdk.Tags.of(app).add("Project", "BankingBICopilot")
cdk.Tags.of(app).add("Phase", "2-KnowledgeBase")
cdk.Tags.of(app).add("ManagedBy", "CDK")

app.synth()
