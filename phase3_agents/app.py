#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.agent_stack import AgentStack

app = cdk.App()

account = app.node.try_get_context("account") or "713520983597"
region  = app.node.try_get_context("region")  or "us-east-1"

env = cdk.Environment(account=account, region=region)

AgentStack(app, "BankingBIAgents",
    account=account,
    region=region,
    env=env,
    description="Phase 3 — Bedrock multi-agent KPI investigation + PDF reports",
)

cdk.Tags.of(app).add("Project", "BankingBICopilot")
cdk.Tags.of(app).add("Phase", "3-Agents")
cdk.Tags.of(app).add("ManagedBy", "CDK")

app.synth()
