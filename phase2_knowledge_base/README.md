# Banking BI Copilot — Phase 2: Knowledge Base

## What this deploys

| Resource | Details |
|---|---|
| S3 bucket | `banking-bi-metric-docs-{account}` — stores governed metric definition documents |
| OpenSearch Serverless | Vector search collection `banking-bi-kb` — stores embeddings |
| Bedrock Knowledge Base | `banking-bi-metric-definitions` — Titan Embeddings V2, 512-token chunks |
| IAM role | `banking-bi-bedrock-kb` — KB service role with S3 + OSS + Bedrock permissions |

## Models used

| Model | Purpose |
|---|---|
| `amazon.titan-embed-text-v2:0` | Embedding metric definitions into vectors |
| `anthropic.claude-sonnet-4-20250514-v1:0` | Agent queries (Phase 3) |

## Metric definitions included

| File | KPIs Covered |
|---|---|
| `nim_definition.md` | Net Interest Margin |
| `npl_ratio_definition.md` | Non-Performing Loan Ratio |
| `casa_roe_cir_lcr_definitions.md` | CASA Ratio, ROE/ROA, CIR, LCR/NSFR |

## Deploy

```powershell
cd C:\Users\anita\banking-bi-copilot\phase2_knowledge_base

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

cdk deploy BankingBIKnowledgeBase --require-approval never
```

## Post-deploy: upload definitions and trigger ingestion

```powershell
python scripts/sync_knowledge_base.py --account 713520983597 --region us-east-1
```

This will:
1. Upload all 3 metric definition files to S3
2. Start a Bedrock ingestion job to embed and index them
3. Wait for completion (takes 2–3 minutes)
4. Run 3 test retrieval queries to verify the KB works

## Re-sync after updating definitions

```powershell
python scripts/sync_knowledge_base.py --account 713520983597 --region us-east-1
```

## Test only (no upload/ingest)

```powershell
python scripts/sync_knowledge_base.py --account 713520983597 --region us-east-1 --test-only
```

## Folder structure

```
phase2_knowledge_base/
├── app.py                          CDK entry point
├── cdk.json                        CDK config
├── requirements.txt
├── stacks/
│   └── knowledge_base_stack.py     Main CDK stack
├── metric_definitions/
│   ├── nim_definition.md           NIM governed definition
│   ├── npl_ratio_definition.md     NPL governed definition
│   └── casa_roe_cir_lcr_definitions.md  CASA, ROE/ROA, CIR, LCR/NSFR
└── scripts/
    └── sync_knowledge_base.py      Upload + ingest + test script
```

## Next: Phase 3 — Agent Orchestration

Phase 3 builds the Bedrock multi-agent system:
- Supervisor agent (Claude Sonnet 4)
- KPI investigation sub-agent
- Driver analysis sub-agent
- Metric validation sub-agent (queries this Knowledge Base)
- Narrative generation sub-agent
