from aws_cdk import (
    Stack, RemovalPolicy, Duration,
    aws_glue as glue,
    aws_glue_alpha as glue_a,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_redshiftserverless as redshift,
)
from constructs import Construct


class GlueStack(Stack):
    """
    Phase 1 — AWS Glue ETL + Data Catalog
    - Glue Database per zone (raw_banking, curated_banking)
    - Crawlers to auto-discover S3 partitions
    - ETL jobs: raw → curated (validate + normalise)
                curated → published (compute KPI aggregates)
    - Glue Workflow to chain crawl → transform → load
    """

    def __init__(self, scope: Construct, construct_id: str,
                 data_lake_bucket: s3.Bucket,
                 redshift_workgroup,
                 **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── Glue service role ─────────────────────────────────────────────────
        self.glue_role = iam.Role(self, "GlueRole",
            role_name="banking-bi-glue-role",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
        )
        self.glue_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSGlueServiceRole"
            )
        )
        data_lake_bucket.grant_read_write(self.glue_role)
        self.glue_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "redshift-serverless:GetWorkgroup",
                "redshift-serverless:GetCredentials",
                "redshift-data:ExecuteStatement",
                "redshift-data:DescribeStatement",
                "redshift-data:GetStatementResult",
                "secretsmanager:GetSecretValue",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
            ],
            resources=["*"],
        ))

        # ── Glue Databases ────────────────────────────────────────────────────
        self.glue_database = glue.CfnDatabase(self, "CuratedDB",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="banking_curated",
                description="Curated banking KPI data — validated Parquet",
            ),
        )

        raw_database = glue.CfnDatabase(self, "RawDB",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="banking_raw",
                description="Raw landing zone — core banking exports",
            ),
        )

        # ── Crawlers ──────────────────────────────────────────────────────────
        kpi_domains = [
            ("nim",         "Net Interest Margin"),
            ("npl_ratio",   "Non-Performing Loan Ratio"),
            ("casa_ratio",  "CASA Ratio"),
            ("roe_roa",     "Return on Equity and Assets"),
            ("cost_income", "Cost-to-Income Ratio"),
            ("lcr_nsfr",    "Liquidity Coverage and NSFR"),
        ]

        for domain_key, domain_label in kpi_domains:
            # Raw zone crawler
            glue.CfnCrawler(self, f"RawCrawler{domain_key.title()}",
                name=f"banking-bi-raw-{domain_key}",
                role=self.glue_role.role_arn,
                database_name="banking_raw",
                targets=glue.CfnCrawler.TargetsProperty(
                    s3_targets=[glue.CfnCrawler.S3TargetProperty(
                        path=f"s3://{data_lake_bucket.bucket_name}/raw/{domain_key}/",
                        exclusions=["_temporary/**", "_staging/**"],
                    )],
                ),
                schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                    update_behavior="LOG",
                    delete_behavior="LOG",
                ),
                recrawl_policy=glue.CfnCrawler.RecrawlPolicyProperty(
                    recrawl_behavior="CRAWL_NEW_FOLDERS_ONLY",
                ),
                description=f"Crawls raw {domain_label} exports",
            )

            # Curated zone crawler
            glue.CfnCrawler(self, f"CuratedCrawler{domain_key.title()}",
                name=f"banking-bi-curated-{domain_key}",
                role=self.glue_role.role_arn,
                database_name="banking_curated",
                targets=glue.CfnCrawler.TargetsProperty(
                    s3_targets=[glue.CfnCrawler.S3TargetProperty(
                        path=f"s3://{data_lake_bucket.bucket_name}/curated/{domain_key}/",
                        exclusions=["_temporary/**"],
                    )],
                ),
                schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                    update_behavior="LOG",
                    delete_behavior="LOG",
                ),
                description=f"Crawls curated {domain_label} Parquet",
            )

        # ── ETL Job: raw → curated ─────────────────────────────────────────────
        glue.CfnJob(self, "RawToCuratedJob",
            name="banking-bi-raw-to-curated",
            role=self.glue_role.role_arn,
            description="Validates, cleanses, and converts raw exports to Parquet",
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                python_version="3",
                script_location=(
                    f"s3://{data_lake_bucket.bucket_name}"
                    "/glue-scripts/raw_to_curated.py"
                ),
            ),
            glue_version="4.0",
            worker_type="G.1X",
            number_of_workers=5,
            timeout=120,
            default_arguments={
                "--job-language": "python",
                "--enable-metrics": "true",
                "--enable-continuous-cloudwatch-log": "true",
                "--enable-spark-ui": "true",
                "--spark-event-logs-path": (
                    f"s3://{data_lake_bucket.bucket_name}/spark-logs/"
                ),
                "--SOURCE_BUCKET": data_lake_bucket.bucket_name,
                "--TARGET_BUCKET": data_lake_bucket.bucket_name,
                "--DATABASE_NAME": "banking_raw",
                "--TempDir": (
                    f"s3://{data_lake_bucket.bucket_name}/glue-temp/"
                ),
            },
            execution_property=glue.CfnJob.ExecutionPropertyProperty(
                max_concurrent_runs=3,
            ),
        )

        # ── ETL Job: curated → published (KPI aggregation) ────────────────────
        glue.CfnJob(self, "CuratedToPublishedJob",
            name="banking-bi-curated-to-published",
            role=self.glue_role.role_arn,
            description="Computes KPI aggregates and loads to published zone + Redshift",
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                python_version="3",
                script_location=(
                    f"s3://{data_lake_bucket.bucket_name}"
                    "/glue-scripts/curated_to_published.py"
                ),
            ),
            glue_version="4.0",
            worker_type="G.2X",
            number_of_workers=10,
            timeout=180,
            default_arguments={
                "--job-language": "python",
                "--enable-metrics": "true",
                "--enable-continuous-cloudwatch-log": "true",
                "--SOURCE_BUCKET": data_lake_bucket.bucket_name,
                "--TARGET_BUCKET": data_lake_bucket.bucket_name,
                "--REDSHIFT_CLUSTER": "banking-bi-aurora",
                "--DB_NAME": "banking_bi",
                "--TempDir": (
                    f"s3://{data_lake_bucket.bucket_name}/glue-temp/"
                ),
            },
        )

        # ── Glue Workflow ──────────────────────────────────────────────────────
        workflow = glue.CfnWorkflow(self, "ETLWorkflow",
            name="banking-bi-etl-pipeline",
            description="Full pipeline: crawl raw → transform → publish → load Redshift",
        )

        # ── Glue Workflow Triggers ────────────────────────────────────────────
        # A Glue workflow can only have ONE starting trigger.
        # Strategy: single scheduled trigger starts the raw->curated job.
        # The job itself calls the crawlers programmatically before processing.

        # Trigger 1 (ONLY starting trigger): daily schedule → raw-to-curated job
        glue.CfnTrigger(self, "ScheduleTrigger",
            name="banking-bi-daily-start",
            type="SCHEDULED",
            schedule="cron(0 2 * * ? *)",
            workflow_name=workflow.name,
            actions=[glue.CfnTrigger.ActionProperty(
                job_name="banking-bi-raw-to-curated",
            )],
            start_on_creation=True,
        )

        # Trigger 2: raw-to-curated succeeded → curated-to-published job
        glue.CfnTrigger(self, "RawToCuratedTrigger",
            name="banking-bi-raw-to-curated-trigger",
            type="CONDITIONAL",
            workflow_name=workflow.name,
            predicate=glue.CfnTrigger.PredicateProperty(
                logical="AND",
                conditions=[glue.CfnTrigger.ConditionProperty(
                    logical_operator="EQUALS",
                    job_name="banking-bi-raw-to-curated",
                    state="SUCCEEDED",
                )],
            ),
            actions=[glue.CfnTrigger.ActionProperty(
                job_name="banking-bi-curated-to-published",
            )],
            start_on_creation=True,
        )

        # Triggers 3a/3b/3c: curated-to-published done → curated crawlers in pairs
        domain_keys = [d for d, _ in kpi_domains]
        crawler_batches = [domain_keys[0:2], domain_keys[2:4], domain_keys[4:6]]

        for i, batch in enumerate(crawler_batches):
            glue.CfnTrigger(self, f"CuratedCrawlTrigger{i}",
                name=f"banking-bi-curated-crawl-{i}",
                type="CONDITIONAL",
                workflow_name=workflow.name,
                predicate=glue.CfnTrigger.PredicateProperty(
                    logical="AND",
                    conditions=[glue.CfnTrigger.ConditionProperty(
                        logical_operator="EQUALS",
                        job_name="banking-bi-curated-to-published",
                        state="SUCCEEDED",
                    )],
                ),
                actions=[
                    glue.CfnTrigger.ActionProperty(
                        crawler_name=f"banking-bi-curated-{d}"
                    ) for d in batch
                ],
                start_on_creation=True,
            )
