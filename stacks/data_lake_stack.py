from aws_cdk import (
    Stack, RemovalPolicy, Duration,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_kms as kms,
    aws_iam as iam,
)
from constructs import Construct


class DataLakeStack(Stack):
    """
    Phase 1 — S3 Data Lake
    Three-zone architecture:
      raw/      — immutable landing zone (core banking exports)
      curated/  — cleaned & validated Parquet, partitioned by KPI/date
      published/ — aggregated, BI-ready tables consumed by Redshift
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── KMS key for at-rest encryption ───────────────────────────────────
        self.lake_key = kms.Key(self, "LakeKey",
            description="Banking BI data lake encryption key",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,
        )
        self.lake_key.add_alias("alias/banking-bi-lake")

        # ── Access log bucket ─────────────────────────────────────────────────
        log_bucket = s3.Bucket(self, "LakeAccessLogs",
            bucket_name=f"banking-bi-access-logs-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            enforce_ssl=True,
        )

        # ── Main lake bucket ──────────────────────────────────────────────────
        self.lake_bucket = s3.Bucket(self, "LakeBucket",
            bucket_name=f"banking-bi-lake-{self.account}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.lake_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            server_access_logs_bucket=log_bucket,
            server_access_logs_prefix="lake-access/",
            removal_policy=RemovalPolicy.RETAIN,
            enforce_ssl=True,
            lifecycle_rules=[
                # Raw zone — move to IA after 90 days, Glacier after 1 year
                s3.LifecycleRule(
                    id="RawZoneLifecycle",
                    prefix="raw/",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(90),
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(365),
                        ),
                    ],
                ),
                # Published zone — expire old aggregates after 2 years
                s3.LifecycleRule(
                    id="PublishedZoneLifecycle",
                    prefix="published/",
                    expiration=Duration.days(730),
                ),
            ],
        )

        # ── Bucket structure (placeholder objects define zone prefixes) ────────
        # Zones & KPI subdirectories created as zero-byte prefix markers
        zones = ["raw", "curated", "published"]
        kpi_domains = [
            "nim",          # Net Interest Margin
            "npl_ratio",    # Non-Performing Loan Ratio
            "casa_ratio",   # Current & Savings Account Ratio
            "roe_roa",      # Return on Equity / Assets
            "cost_income",  # Cost-to-Income Ratio
            "lcr_nsfr",     # Liquidity Coverage / Net Stable Funding Ratios
        ]

        for zone in zones:
            for domain in kpi_domains:
                # Creates logical prefix structure; Glue jobs write real data
                self.lake_bucket.add_lifecycle_rule(
                    id=f"Abort-{zone}-{domain}",
                    prefix=f"{zone}/{domain}/",
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                )

        # ── Bucket policy — deny non-SSL and enforce KMS ──────────────────────
        self.lake_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="DenyNonKMSUploads",
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:PutObject"],
                resources=[self.lake_bucket.arn_for_objects("*")],
                conditions={
                    "StringNotEquals": {
                        "s3:x-amz-server-side-encryption-aws-kms-key-id":
                            self.lake_key.key_arn
                    }
                },
            )
        )
