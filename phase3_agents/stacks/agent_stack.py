from aws_cdk import (
    Stack, RemovalPolicy, CfnOutput, Duration,
    aws_bedrock as bedrock,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_dynamodb as dynamodb,
    aws_sns as sns,
    aws_apigateway as apigw,
)
from constructs import Construct
import json


class AgentStack(Stack):
    """
    Phase 3 — Bedrock Multi-Agent Orchestration (fully managed)

    Agents:
      - Supervisor agent (Claude Sonnet 4) — routes and synthesises
      - KPI Investigation sub-agent — queries RDS for KPI data
      - Driver Analysis sub-agent   — identifies movement drivers
      - Metric Validation sub-agent — validates against S3 definitions
      - Narrative Generation sub-agent — writes executive PDF

    Triggers:
      - Event-driven: EventBridge anomaly rule → supervisor agent
      - Conversational: API Gateway → supervisor agent

    Output:
      - PDF report → S3 → SNS notification
    """

    MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"

    def __init__(self, scope: Construct, construct_id: str,
                 account: str, region: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── DynamoDB — session state ───────────────────────────────────────────
        self.session_table = dynamodb.Table(self, "SessionTable",
            table_name="banking-bi-agent-sessions",
            partition_key=dynamodb.Attribute(
                name="session_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
        )

        # ── SNS — PDF delivery ─────────────────────────────────────────────────
        self.summary_topic = sns.Topic(self, "SummaryTopic",
            topic_name="banking-bi-executive-summaries",
            display_name="Banking BI Executive PDF Reports",
        )

        # ── S3 — PDF output bucket ─────────────────────────────────────────────
        self.output_bucket = s3.Bucket(self, "OutputBucket",
            bucket_name=f"banking-bi-reports-{account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True,
        )

        # ── IAM role for Bedrock agents ────────────────────────────────────────
        self.agent_role = iam.Role(self, "AgentRole",
            role_name="banking-bi-bedrock-agent",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": account},
                }
            ),
        )
        self.agent_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[
                f"arn:aws:bedrock:{region}::foundation-model/{self.MODEL_ID}"
            ],
        ))
        self.agent_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeAgent"],
            resources=[f"arn:aws:bedrock:{region}:{account}:agent/*"],
        ))
        self.agent_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            resources=[
                self.output_bucket.bucket_arn,
                f"{self.output_bucket.bucket_arn}/*",
                f"arn:aws:s3:::banking-bi-metric-docs-{account}",
                f"arn:aws:s3:::banking-bi-metric-docs-{account}/*",
            ],
        ))

        # ── IAM role for Lambda action group functions ─────────────────────────
        lambda_role = iam.Role(self, "LambdaRole",
            role_name="banking-bi-agent-lambda",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "rds:DescribeDBInstances",
                "rds-data:ExecuteStatement",
                "secretsmanager:GetSecretValue",
                "bedrock:InvokeModel",
                "bedrock:InvokeAgent",
                "s3:GetObject", "s3:PutObject", "s3:ListBucket",
                "dynamodb:PutItem", "dynamodb:GetItem",
                "dynamodb:UpdateItem", "dynamodb:Query",
                "sns:Publish",
                "ssm:GetParameters", "ssm:GetParameter",
                "lambda:InvokeFunction",
            ],
            resources=["*"],
        ))

        common_env = {
            "SESSION_TABLE":      self.session_table.table_name,
            "SUMMARY_TOPIC_ARN":  self.summary_topic.topic_arn,
            "OUTPUT_BUCKET":      self.output_bucket.bucket_name,
            "MODEL_ID":           self.MODEL_ID,
            "REGION":             region,
            "ACCOUNT":            account,
            "RDS_SECRET_ARN": (
                f"arn:aws:secretsmanager:{region}:{account}"
                ":secret:banking-bi/rds/admin"
            ),
            "RDS_DB_NAME": "banking_bi",
            "METRIC_DOCS_BUCKET": f"banking-bi-metric-docs-{account}",
        }

        # ── Lambda: KPI data action group ──────────────────────────────────────
        self.kpi_lambda = lambda_.Function(self, "KPILambda",
            function_name="banking-bi-kpi-action",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="kpi_action.handler",
            code=lambda_.Code.from_asset("lambda_functions"),
            timeout=Duration.minutes(5),
            memory_size=512,
            role=lambda_role,
            environment=common_env,
        )

        # ── Lambda: Driver analysis action group ───────────────────────────────
        self.driver_lambda = lambda_.Function(self, "DriverLambda",
            function_name="banking-bi-driver-action",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="driver_action.handler",
            code=lambda_.Code.from_asset("lambda_functions"),
            timeout=Duration.minutes(5),
            memory_size=512,
            role=lambda_role,
            environment=common_env,
        )

        # ── Lambda: Metric validation action group ─────────────────────────────
        self.validation_lambda = lambda_.Function(self, "ValidationLambda",
            function_name="banking-bi-validation-action",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="validation_action.handler",
            code=lambda_.Code.from_asset("lambda_functions"),
            timeout=Duration.minutes(3),
            memory_size=256,
            role=lambda_role,
            environment=common_env,
        )

        # ── Lambda: PDF generation action group ────────────────────────────────
        self.pdf_lambda = lambda_.Function(self, "PDFLambda",
            function_name="banking-bi-pdf-action",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="pdf_action.handler",
            code=lambda_.Code.from_asset("lambda_functions"),
            timeout=Duration.minutes(10),
            memory_size=1024,
            role=lambda_role,
            environment=common_env,

        )

        # ── Lambda: Supervisor orchestrator (invokes Bedrock agents) ──────────
        self.supervisor_lambda = lambda_.Function(self, "SupervisorLambda",
            function_name="banking-bi-supervisor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="supervisor.handler",
            code=lambda_.Code.from_asset("lambda_functions"),
            timeout=Duration.minutes(15),
            memory_size=1024,
            role=lambda_role,
            environment={
                **common_env,
                "KPI_LAMBDA":        self.kpi_lambda.function_name,
                "DRIVER_LAMBDA":     self.driver_lambda.function_name,
                "VALIDATION_LAMBDA": self.validation_lambda.function_name,
                "PDF_LAMBDA":        self.pdf_lambda.function_name,
            },
        )

        # Lambda role already has lambda:InvokeFunction via policy above

        # ── Allow Bedrock to invoke action group lambdas ──────────────────────
        bedrock_fns = [
            ("KPI",        self.kpi_lambda),
            ("Driver",     self.driver_lambda),
            ("Validation", self.validation_lambda),
            ("PDF",        self.pdf_lambda),
            ("Supervisor", self.supervisor_lambda),
        ]
        for label, fn in bedrock_fns:
            fn.add_permission(
                f"BedrockInvoke{label}",
                principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
                source_arn=f"arn:aws:bedrock:{region}:{account}:agent/*",
            )

        # ── Bedrock Agent: KPI Investigation sub-agent ─────────────────────────
        kpi_agent = bedrock.CfnAgent(self, "KPIAgent",
            agent_name="banking-bi-kpi-investigation",
            description="Queries RDS for current KPI values and detects anomalies",
            agent_resource_role_arn=self.agent_role.role_arn,
            foundation_model=self.MODEL_ID,
            instruction="""You are a banking KPI investigation specialist.
Your role is to query the banking database for current KPI values,
identify anomalies, and provide precise quantitative analysis.

When investigating KPIs:
1. Always retrieve current value AND historical comparison (WoW, MoM, YoY)
2. Identify which business units and products are driving changes
3. Flag any metrics breaching alert thresholds
4. Provide basis point changes, not just percentages
5. Never interpret — only report what the data shows

Use the get_kpi_data action to retrieve KPI information.
Use the get_kpi_breakdown action for segment/product details.""",
            auto_prepare=True,
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="kpi-data-actions",
                    description="Actions to retrieve KPI data from the banking database",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.kpi_lambda.function_arn,
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="get_kpi_data",
                                description="Retrieve current KPI values and trends",
                                parameters={
                                    "kpi_names": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Comma-separated KPI names: nim,npl_ratio,casa_ratio,roe_roa,cost_income,lcr_nsfr",
                                        required=True,
                                    ),
                                    "period": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Period: daily, mtd, qtd, ytd",
                                        required=False,
                                    ),
                                }
                            ),
                            bedrock.CfnAgent.FunctionProperty(
                                name="get_kpi_breakdown",
                                description="Get KPI breakdown by business unit, product, or geography",
                                parameters={
                                    "kpi_name": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="KPI name to break down",
                                        required=True,
                                    ),
                                    "dimension": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Breakdown dimension: business_unit, product, region",
                                        required=True,
                                    ),
                                }
                            ),
                        ]
                    ),
                )
            ],
        )

        # ── Bedrock Agent: Driver Analysis sub-agent ───────────────────────────
        driver_agent = bedrock.CfnAgent(self, "DriverAgent",
            agent_name="banking-bi-driver-analysis",
            description="Identifies likely drivers of KPI movements",
            agent_resource_role_arn=self.agent_role.role_arn,
            foundation_model=self.MODEL_ID,
            instruction="""You are a banking analytics expert specialising
in root cause analysis of KPI movements.

Your role is to identify the 3-5 most likely drivers of observed
KPI changes, ranked by confidence. For each driver provide:
- Clear description of the driver
- Supporting data evidence
- Confidence level (high/medium/low)
- Which KPIs are affected

Focus on:
- Mix shifts (product, customer segment, geography)
- Rate movements (pricing, funding costs)
- Volume changes (new business, runoff, attrition)
- Credit quality changes (NPL migration, provision movements)
- External factors (macro, regulatory, seasonal)

Use the analyse_drivers action to run correlation analysis.""",
            auto_prepare=True,
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="driver-analysis-actions",
                    description="Actions to analyse KPI movement drivers",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.driver_lambda.function_arn,
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="analyse_drivers",
                                description="Analyse drivers of KPI movements using segment correlation",
                                parameters={
                                    "kpi_name": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="KPI to analyse drivers for",
                                        required=True,
                                    ),
                                    "change_direction": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Direction of change: up or down",
                                        required=True,
                                    ),
                                }
                            ),
                        ]
                    ),
                )
            ],
        )

        # ── Bedrock Agent: Metric Validation sub-agent ─────────────────────────
        validation_agent = bedrock.CfnAgent(self, "ValidationAgent",
            agent_name="banking-bi-metric-validation",
            description="Validates KPI calculations against governed definitions",
            agent_resource_role_arn=self.agent_role.role_arn,
            foundation_model=self.MODEL_ID,
            instruction="""You are a banking governance and compliance specialist.

Your role is to validate that KPI calculations conform to the bank's
official governed metric definitions. For each KPI:
1. Retrieve the official definition from the metric definitions library
2. Compare the actual calculation method against the definition
3. Verify data sources match the governed sources
4. Confirm thresholds align with policy
5. Flag any deviations with severity

Never approve a KPI that uses a non-standard formula.
Always cite the specific section of the definition document.

Use the validate_metric action to perform validation.""",
            auto_prepare=True,
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="validation-actions",
                    description="Actions to validate metric calculations",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.validation_lambda.function_arn,
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="validate_metric",
                                description="Validate a KPI calculation against its governed definition",
                                parameters={
                                    "kpi_name": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="KPI to validate",
                                        required=True,
                                    ),
                                }
                            ),
                        ]
                    ),
                )
            ],
        )

        # ── Bedrock Agent: Supervisor (orchestrates sub-agents) ────────────────
        # Sub-agent ARNs are set after agents are created
        self.supervisor_agent = bedrock.CfnAgent(self, "SupervisorAgent",
            agent_name="banking-bi-supervisor",
            description="Orchestrates KPI investigation and generates executive PDF reports",
            agent_resource_role_arn=self.agent_role.role_arn,
            foundation_model=self.MODEL_ID,
            instruction="""You are the Banking BI Copilot supervisor agent.
You orchestrate a team of specialist sub-agents to investigate
KPI movements and produce executive-grade PDF reports.

INVESTIGATION WORKFLOW:
1. Receive investigation request (anomaly event or user question)
2. Delegate to KPI Investigation agent to retrieve current data
3. Delegate to Driver Analysis agent to identify root causes
4. Delegate to Metric Validation agent to confirm calculations
5. Synthesise all findings into a coherent narrative
6. Generate PDF executive report via the pdf_report action
7. Deliver report via SNS notification

REPORT STANDARDS:
- Every KPI cited must be validated by the Metric Validation agent
- Every driver claim must have supporting data evidence
- Risk flags must reference specific regulatory thresholds
- Recommended actions must be specific and actionable
- Language must be appropriate for CEO/Board audience

Always complete all four investigation steps before generating the PDF.""",
            auto_prepare=True,
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="pdf-report-actions",
                    description="Actions to generate and deliver PDF executive reports",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.pdf_lambda.function_arn,
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="generate_pdf_report",
                                description="Generate an executive PDF report from investigation findings",
                                parameters={
                                    "session_id": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Investigation session ID",
                                        required=True,
                                    ),
                                    "headline": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="One-sentence headline finding",
                                        required=True,
                                    ),
                                    "findings_json": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="JSON string of all investigation findings",
                                        required=True,
                                    ),
                                    "risk_level": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Overall risk level: low, medium, high, critical",
                                        required=True,
                                    ),
                                }
                            ),
                            bedrock.CfnAgent.FunctionProperty(
                                name="deliver_report",
                                description="Deliver completed PDF report via SNS to executives",
                                parameters={
                                    "session_id": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Session ID of completed report",
                                        required=True,
                                    ),
                                    "recipient_group": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Recipient group: board, exco, cro, cfo, all",
                                        required=False,
                                    ),
                                }
                            ),
                        ]
                    ),
                )
            ],
            # Sub-agents wired post-deploy via configure_agents.py
        )

        # ── Agent aliases (required for invocation) ────────────────────────────
        kpi_alias = bedrock.CfnAgentAlias(self, "KPIAlias",
            agent_id=kpi_agent.attr_agent_id,
            agent_alias_name="live",
            description="KPI Investigation agent live alias",
        )
        driver_alias = bedrock.CfnAgentAlias(self, "DriverAlias",
            agent_id=driver_agent.attr_agent_id,
            agent_alias_name="live",
            description="Driver Analysis agent live alias",
        )
        validation_alias = bedrock.CfnAgentAlias(self, "ValidationAlias",
            agent_id=validation_agent.attr_agent_id,
            agent_alias_name="live",
            description="Metric Validation agent live alias",
        )
        supervisor_alias = bedrock.CfnAgentAlias(self, "SupervisorAlias",
            agent_id=self.supervisor_agent.attr_agent_id,
            agent_alias_name="live",
            description="Supervisor agent live alias",
        )

        # ── API Gateway — conversational trigger ───────────────────────────────
        api = apigw.RestApi(self, "BIApi",
            rest_api_name="banking-bi-copilot",
            description="Banking BI Copilot conversational API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["POST", "OPTIONS"],
            ),
        )

        investigate_resource = api.root.add_resource("investigate")
        investigate_resource.add_method(
            "POST",
            apigw.LambdaIntegration(self.supervisor_lambda),
        )

        chat_resource = api.root.add_resource("chat")
        chat_resource.add_method(
            "POST",
            apigw.LambdaIntegration(self.supervisor_lambda),
        )

        # ── EventBridge — anomaly trigger ──────────────────────────────────────
        anomaly_rule = events.Rule(self, "AnomalyRule",
            rule_name="banking-bi-kpi-anomaly",
            description="Triggers agent investigation when KPI anomaly detected",
            event_pattern=events.EventPattern(
                source=["banking-bi.etl"],
                detail_type=["KPI Anomaly Detected"],
            ),
        )
        anomaly_rule.add_target(
            targets.LambdaFunction(self.supervisor_lambda)
        )

        # ── EventBridge — daily schedule ───────────────────────────────────────
        daily_rule = events.Rule(self, "DailyRule",
            rule_name="banking-bi-daily-report",
            description="Daily executive report at 06:00 UTC",
            schedule=events.Schedule.cron(hour="6", minute="0"),
        )
        daily_rule.add_target(
            targets.LambdaFunction(
                self.supervisor_lambda,
                event=events.RuleTargetInput.from_object({
                    "trigger": "scheduled",
                    "kpis": ["nim", "npl_ratio", "casa_ratio",
                             "roe_roa", "cost_income", "lcr_nsfr"],
                    "output_format": "pdf",
                    "recipient_group": "exco",
                }),
            )
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(self, "SupervisorAgentId",
            value=self.supervisor_agent.attr_agent_id,
            export_name="BankingBI-SupervisorAgentId",
        )
        CfnOutput(self, "SupervisorAliasId",
            value=supervisor_alias.attr_agent_alias_id,
            export_name="BankingBI-SupervisorAliasId",
        )
        CfnOutput(self, "KPIAgentId",
            value=kpi_agent.attr_agent_id,
            export_name="BankingBI-KPIAgentId",
        )
        CfnOutput(self, "KPIAliasId",
            value=kpi_alias.attr_agent_alias_id,
            export_name="BankingBI-KPIAliasId",
        )
        CfnOutput(self, "DriverAgentId",
            value=driver_agent.attr_agent_id,
            export_name="BankingBI-DriverAgentId",
        )
        CfnOutput(self, "ValidationAgentId",
            value=validation_agent.attr_agent_id,
            export_name="BankingBI-ValidationAgentId",
        )
        CfnOutput(self, "ApiEndpoint",
            value=api.url,
            export_name="BankingBI-ApiEndpoint",
        )
        CfnOutput(self, "ChatEndpoint",
            value=f"{api.url}chat",
            export_name="BankingBI-ChatEndpoint",
        )
        CfnOutput(self, "OutputBucketName",
            value=self.output_bucket.bucket_name,
            export_name="BankingBI-ReportsBucket",
        )
        CfnOutput(self, "SummaryTopicArn",
            value=self.summary_topic.topic_arn,
            export_name="BankingBI-SummaryTopic",
        )
        CfnOutput(self, "SessionTableName",
            value=self.session_table.table_name,
            export_name="BankingBI-SessionTable",
        )
