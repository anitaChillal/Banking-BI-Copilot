from aws_cdk import (
    Stack, RemovalPolicy, CfnOutput, Duration,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_kms as kms,
    aws_secretsmanager as sm,
    aws_s3 as s3,
)
from constructs import Construct


class RedshiftStack(Stack):
    """
    Phase 1 — RDS PostgreSQL 15 KPI Warehouse
    Works on all AWS accounts including free tier (db.t3.micro).
    Same SQL interface as Redshift — KPI schema unchanged.
    Migrate to Redshift/Aurora later by swapping this stack only.
    """

    def __init__(self, scope: Construct, construct_id: str,
                 data_lake_bucket: s3.Bucket, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── VPC ───────────────────────────────────────────────────────────────
        self.vpc = ec2.Vpc(self, "RdsVpc",
            vpc_name="banking-bi-rds-vpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=28,
                ),
            ],
        )

        # ── Security group ────────────────────────────────────────────────────
        self.sg = ec2.SecurityGroup(self, "RdsSG",
            vpc=self.vpc,
            description="Banking BI RDS PostgreSQL",
            allow_all_outbound=True,
        )
        self.sg.add_ingress_rule(
            self.sg, ec2.Port.tcp(5432), "PostgreSQL within VPC"
        )

        # ── Admin credentials ─────────────────────────────────────────────────
        self.admin_secret = sm.Secret(self, "RdsAdminSecret",
            secret_name="banking-bi/rds/admin",
            description="RDS PostgreSQL admin credentials",
            generate_secret_string=sm.SecretStringGenerator(
                secret_string_template='{"username":"rsadmin"}',
                generate_string_key="password",
                exclude_punctuation=True,
                password_length=32,
            ),
        )

        # ── IAM role for S3 access ────────────────────────────────────────────
        self.spectrum_role = iam.Role(self, "RdsS3Role",
            role_name="banking-bi-rds-s3",
            assumed_by=iam.ServicePrincipal("rds.amazonaws.com"),
            description="Allows RDS to import from S3 data lake",
        )
        data_lake_bucket.grant_read(self.spectrum_role)
        self.spectrum_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "glue:GetDatabase", "glue:GetDatabases",
                "glue:GetTable", "glue:GetTables",
                "glue:GetPartitions",
            ],
            resources=["*"],
        ))

        # ── RDS PostgreSQL 15 — free tier eligible (db.t3.micro) ─────────────
        self.cluster = rds.DatabaseInstance(self, "RdsInstance",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15,
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MICRO,       # free tier eligible
            ),
            credentials=rds.Credentials.from_secret(self.admin_secret),
            database_name="banking_bi",
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            security_groups=[self.sg],
            storage_encrypted=True,
            allocated_storage=20,             # 20 GB — free tier maximum
            max_allocated_storage=100,        # auto-scales up to 100 GB
            backup_retention=Duration.days(1),
            delete_automated_backups=True,
            deletion_protection=False,
            removal_policy=RemovalPolicy.DESTROY,
            cloudwatch_logs_exports=["postgresql"],
            enable_performance_insights=False, # not available on t3.micro
            publicly_accessible=False,
        )

        # Alias so app.py and GlueStack references stay unchanged
        self.workgroup = self.cluster

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(self, "DbEndpoint",
            value=self.cluster.db_instance_endpoint_address,
            export_name="BankingBI-RdsEndpoint",
        )
        CfnOutput(self, "DbPort",
            value=self.cluster.db_instance_endpoint_port,
            export_name="BankingBI-RdsPort",
        )
        CfnOutput(self, "AdminSecretArn",
            value=self.admin_secret.secret_arn,
            export_name="BankingBI-RdsAdminSecretArn",
        )
        CfnOutput(self, "S3RoleArn",
            value=self.spectrum_role.role_arn,
            export_name="BankingBI-RdsS3RoleArn",
        )
        CfnOutput(self, "DatabaseName",
            value="banking_bi",
            export_name="BankingBI-DatabaseName",
        )
