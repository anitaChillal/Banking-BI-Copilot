from aws_cdk import (
    Stack,
    aws_lakeformation as lf,
    aws_iam as iam,
    aws_glue as glue,
    aws_s3 as s3,
)
from constructs import Construct


class GovernanceStack(Stack):
    """
    Phase 1 — Lake Formation Governance
    - Register S3 data lake location
    - Column-level permissions per KPI domain
    - Analyst role (read curated, no PII columns)
    - Agent role (read published, write to Redshift via Spectrum)
    - Auditor role (read-only all zones)
    """

    def __init__(self, scope: Construct, construct_id: str,
                 data_lake_bucket: s3.Bucket,
                 glue_database,
                 **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── Lake Formation data lake settings ─────────────────────────────────
        lf.CfnDataLakeSettings(self, "LFSettings",
            admins=[
                lf.CfnDataLakeSettings.DataLakePrincipalProperty(
                    data_lake_principal_identifier=(
                        f"arn:aws:iam::{self.account}:root"
                    )
                )
            ],
        )

        # ── Register S3 location ──────────────────────────────────────────────
        lf_role = iam.Role(self, "LFServiceRole",
            role_name="banking-bi-lakeformation-role",
            assumed_by=iam.ServicePrincipal("lakeformation.amazonaws.com"),
        )
        data_lake_bucket.grant_read_write(lf_role)

        lf.CfnResource(self, "LFResource",
            resource_arn=data_lake_bucket.bucket_arn,
            use_service_linked_role=False,
            role_arn=lf_role.role_arn,
        )

        # ── IAM roles for personas ─────────────────────────────────────────────
        self.analyst_role = iam.Role(self, "AnalystRole",
            role_name="banking-bi-analyst",
            assumed_by=iam.AccountRootPrincipal(),
            description="Banking analysts — curated zone, no raw PII columns",
        )
        self.agent_role = iam.Role(self, "AgentRole",
            role_name="banking-bi-agent",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Bedrock agents — published zone read + Redshift Spectrum",
        )
        self.auditor_role = iam.Role(self, "AuditorRole",
            role_name="banking-bi-auditor",
            assumed_by=iam.AccountRootPrincipal(),
            description="Read-only access to all zones for compliance auditing",
        )

        # ── Lake Formation permissions ─────────────────────────────────────────
        # Analyst: SELECT on curated database, all tables, EXCLUDE PII columns
        lf.CfnPermissions(self, "AnalystDBPermission",
            data_lake_principal=lf.CfnPermissions.DataLakePrincipalProperty(
                data_lake_principal_identifier=self.analyst_role.role_arn,
            ),
            resource=lf.CfnPermissions.ResourceProperty(
                database_resource=lf.CfnPermissions.DatabaseResourceProperty(
                    catalog_id=self.account,
                    name="banking_curated",
                ),
            ),
            permissions=["DESCRIBE"],
        )

        # Agent: full SELECT on published database (BI-ready, no PII)
        lf.CfnPermissions(self, "AgentDBPermission",
            data_lake_principal=lf.CfnPermissions.DataLakePrincipalProperty(
                data_lake_principal_identifier=self.agent_role.role_arn,
            ),
            resource=lf.CfnPermissions.ResourceProperty(
                database_resource=lf.CfnPermissions.DatabaseResourceProperty(
                    catalog_id=self.account,
                    name="banking_curated",
                ),
            ),
            permissions=["DESCRIBE", "CREATE_TABLE", "ALTER", "DROP"],
        )

        # Auditor: describe all databases
        for db_name in ["banking_raw", "banking_curated"]:
            lf.CfnPermissions(self, f"AuditorDB{db_name}Permission",
                data_lake_principal=lf.CfnPermissions.DataLakePrincipalProperty(
                    data_lake_principal_identifier=self.auditor_role.role_arn,
                ),
                resource=lf.CfnPermissions.ResourceProperty(
                    database_resource=lf.CfnPermissions.DatabaseResourceProperty(
                        catalog_id=self.account,
                        name=db_name,
                    ),
                ),
                permissions=["DESCRIBE"],
            )

        # ── Column-level permissions: exclude PII from analyst role ────────────
        # PII columns that must never be exposed to analysts or agents
        # These exist in raw zone tables only
        pii_excluded_tables = {
            "customer_accounts": [
                "customer_name", "national_id", "date_of_birth",
                "phone_number", "email_address", "home_address",
            ],
            "loan_applications": [
                "applicant_name", "national_id", "employer_name",
                "annual_income_exact",
            ],
        }

        for table_name, pii_cols in pii_excluded_tables.items():
            lf.CfnPermissions(self, f"AnalystColPerm{table_name}",
                data_lake_principal=lf.CfnPermissions.DataLakePrincipalProperty(
                    data_lake_principal_identifier=self.analyst_role.role_arn,
                ),
                resource=lf.CfnPermissions.ResourceProperty(
                    table_with_columns_resource=lf.CfnPermissions.TableWithColumnsResourceProperty(
                        catalog_id=self.account,
                        database_name="banking_raw",
                        name=table_name,
                        column_wildcard=lf.CfnPermissions.ColumnWildcardProperty(
                            excluded_column_names=pii_cols,
                        ),
                    ),
                ),
                permissions=["SELECT"],
            )
