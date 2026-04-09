# Banking BI Copilot — Phase 1: Data Foundation

## What this deploys

| Stack | Resources |
|---|---|
| `BankingBIDataLake` | S3 lake bucket (raw / curated / published zones), KMS key, lifecycle rules |
| `BankingBIRedshift` | Redshift Serverless namespace + workgroup, VPC, Secrets Manager, Spectrum IAM role |
| `BankingBIGlue` | Glue databases, 12 crawlers (raw + curated per KPI), 2 ETL jobs, daily workflow |
| `BankingBIGovernance` | Lake Formation registration, column-level permissions, 3 IAM personas |

## KPI domains covered

- **NIM** — Net Interest Margin (`kpi.net_interest_margin`)
- **NPL Ratio** — Non-Performing Loans (`kpi.npl_ratio`)
- **CASA Ratio** (`kpi.casa_ratio`)
- **ROE / ROA** (`kpi.roe_roa`)
- **Cost-to-Income Ratio** (`kpi.cost_income_ratio`)
- **LCR / NSFR** (`kpi.liquidity_ratios`)

## Prerequisites

```bash
# Python 3.11+
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# AWS CDK CLI
npm install -g aws-cdk

# AWS credentials configured
aws configure
```

## Deploy

```bash
# 1. Bootstrap CDK (once per account/region)
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1

# 2. Edit cdk.json — set account and region

# 3. Synthesise to review
cdk synth

# 4. Deploy all stacks in dependency order
cdk deploy --all --require-approval never

# Or deploy one at a time:
cdk deploy BankingBIDataLake
cdk deploy BankingBIRedshift
cdk deploy BankingBIGlue
cdk deploy BankingBIGovernance
```

## Post-deploy: initialise Redshift schema

```bash
# Get workgroup endpoint from CloudFormation outputs
WORKGROUP=$(aws cloudformation describe-stacks \
  --stack-name BankingBIRedshift \
  --query "Stacks[0].Outputs[?OutputKey=='WorkgroupName'].OutputValue" \
  --output text)

# Get admin password from Secrets Manager
SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name BankingBIRedshift \
  --query "Stacks[0].Outputs[?OutputKey=='AdminSecretArn'].OutputValue" \
  --output text)

# Run DDL via Redshift Data API
aws redshift-data execute-statement \
  --workgroup-name "$WORKGROUP" \
  --database banking_bi \
  --sql file://sql/01_kpi_schema.sql
```

## Upload Glue scripts

```bash
LAKE_BUCKET="banking-bi-lake-$(aws sts get-caller-identity --query Account --output text)"

aws s3 cp glue_scripts/raw_to_curated.py     "s3://$LAKE_BUCKET/glue-scripts/"
aws s3 cp glue_scripts/curated_to_published.py "s3://$LAKE_BUCKET/glue-scripts/"
```

## Data lake folder structure

```
s3://banking-bi-lake-{account}/
├── raw/
│   ├── nim/{year}/{month}/{day}/
│   ├── npl_ratio/...
│   ├── casa_ratio/...
│   ├── roe_roa/...
│   ├── cost_income/...
│   └── lcr_nsfr/...
├── curated/          ← validated Parquet, partitioned
├── published/        ← KPI aggregates for Spectrum + agents
├── quarantine/       ← DQ-failed records
├── glue-scripts/     ← ETL job scripts
├── glue-temp/        ← Glue temp storage
└── spark-logs/       ← Spark UI logs
```

## IAM personas

| Role | Access |
|---|---|
| `banking-bi-analyst` | SELECT on curated zone, PII columns excluded |
| `banking-bi-agent` | SELECT on published zone + kpi schema, INSERT on movement_events |
| `banking-bi-auditor` | Read-only on all zones |

## Next: Phase 2 — Knowledge Base

Phase 2 will ingest governed KPI metric definitions into Amazon Bedrock
Knowledge Base (OpenSearch Serverless) so agents can validate every
calculation they perform against official definitions.
