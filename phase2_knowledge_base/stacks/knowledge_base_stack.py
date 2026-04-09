from aws_cdk import (
    Stack, RemovalPolicy, CfnOutput,
    aws_iam as iam,
    aws_s3 as s3,
    aws_kms as kms,
)
from constructs import Construct


class KnowledgeBaseStack(Stack):
    """
    Phase 2 — S3 docs bucket + IAM role only.
    Bedrock Knowledge Base is created via boto3 script using
    Bedrock's built-in managed vector store (no OpenSearch needed).
    Works on all AWS accounts with no service subscriptions.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── S3 bucket for metric definition documents ─────────────────────────
        self.docs_bucket = s3.Bucket(self, "DocsBucket",
            bucket_name=f"banking-bi-metric-docs-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True,
        )

        # ── IAM role for Bedrock Knowledge Base ───────────────────────────────
        self.kb_role = iam.Role(self, "KBRole",
            role_name="banking-bi-bedrock-kb",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": self.account}
                }
            ),
            description="Bedrock Knowledge Base service role",
        )

        # S3 read access
        self.docs_bucket.grant_read(self.kb_role)

        # Titan Embeddings invocation
        self.kb_role.add_to_policy(iam.PolicyStatement(
            sid="BedrockInvokeEmbeddings",
            actions=["bedrock:InvokeModel"],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/"
                "amazon.titan-embed-text-v2:0"
            ],
        ))

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(self, "DocsBucketName",
            value=self.docs_bucket.bucket_name,
            export_name="BankingBI-MetricDocsBucket",
        )
        CfnOutput(self, "KBRoleArn",
            value=self.kb_role.role_arn,
            export_name="BankingBI-KBRoleArn",
        )
        CfnOutput(self, "AccountId",
            value=self.account,
            export_name="BankingBI-AccountId",
        )
        CfnOutput(self, "Region",
            value=self.region,
            export_name="BankingBI-Region",
        )
