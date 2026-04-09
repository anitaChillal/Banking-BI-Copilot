#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.data_lake_stack import DataLakeStack
from stacks.redshift_stack import RedshiftStack
from stacks.glue_stack import GlueStack
from stacks.governance_stack import GovernanceStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1",
)

data_lake = DataLakeStack(app, "BankingBIDataLake", env=env,
    description="Phase 1 — S3 data lake with zone partitioning")

redshift = RedshiftStack(app, "BankingBIRedshift", env=env,
    data_lake_bucket=data_lake.lake_bucket,
    description="Phase 1 — Redshift Serverless KPI warehouse")

glue = GlueStack(app, "BankingBIGlue", env=env,
    data_lake_bucket=data_lake.lake_bucket,
    redshift_workgroup=redshift.workgroup,
    description="Phase 1 — Glue ETL jobs and Data Catalog")

governance = GovernanceStack(app, "BankingBIGovernance", env=env,
    data_lake_bucket=data_lake.lake_bucket,
    glue_database=glue.glue_database,
    description="Phase 1 — Lake Formation column-level governance")

# Explicit dependencies
redshift.add_dependency(data_lake)
glue.add_dependency(redshift)
governance.add_dependency(glue)

cdk.Tags.of(app).add("Project", "BankingBICopilot")
cdk.Tags.of(app).add("Phase", "1-DataFoundation")
cdk.Tags.of(app).add("ManagedBy", "CDK")

app.synth()
