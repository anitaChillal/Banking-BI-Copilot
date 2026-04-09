"""
Glue ETL Job: raw_to_curated
Phase 1 — Banking BI Copilot

Reads raw core banking exports from S3 (CSV/Parquet),
applies validation rules, normalises schemas, and writes
clean Parquet to the curated zone partitioned by kpi_domain/year/month/day.
"""
import sys
import logging
from datetime import datetime, date

from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame

from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DecimalType,
    IntegerType, DateType, BooleanType, TimestampType,
)

# ── Bootstrap ──────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

args = getResolvedOptions(sys.argv, [
    "JOB_NAME",
    "SOURCE_BUCKET",
    "TARGET_BUCKET",
    "DATABASE_NAME",
    "TempDir",
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

SOURCE_BUCKET = args["SOURCE_BUCKET"]
TARGET_BUCKET = args["TARGET_BUCKET"]
RUN_DATE = date.today()

# ── Validation helpers ─────────────────────────────────────────────────────────

def add_validation_columns(df, domain: str):
    """Add data quality flags without dropping rows — flag bad data for review."""
    df = df.withColumn("_dq_domain", F.lit(domain))
    df = df.withColumn("_dq_processed_at", F.current_timestamp())
    df = df.withColumn("_dq_source_partition",
        F.lit(f"raw/{domain}/{RUN_DATE.strftime('%Y/%m/%d')}"))
    return df


def validate_loan_positions(df):
    """Business rules for loan_positions raw table."""
    df = df.withColumn("_dq_pass", F.lit(True))

    # Outstanding balance must be non-negative
    df = df.withColumn("_dq_pass",
        F.when(F.col("outstanding_balance") < 0, F.lit(False))
         .otherwise(F.col("_dq_pass")))

    # Interest rate must be 0–100%
    df = df.withColumn("_dq_pass",
        F.when((F.col("interest_rate") < 0) | (F.col("interest_rate") > 100),
               F.lit(False))
         .otherwise(F.col("_dq_pass")))

    # Days past due must be non-negative
    df = df.withColumn("_dq_pass",
        F.when(F.col("days_past_due") < 0, F.lit(False))
         .otherwise(F.col("_dq_pass")))

    # Loan status must be known value
    valid_statuses = ["Current", "30DPD", "60DPD", "90DPD", "NPL", "Written-off"]
    df = df.withColumn("_dq_pass",
        F.when(~F.col("loan_status").isin(valid_statuses), F.lit(False))
         .otherwise(F.col("_dq_pass")))

    # Derive NPL flag (DPD >= 90 or status = NPL)
    df = df.withColumn("is_npl",
        (F.col("days_past_due") >= 90) | (F.col("loan_status") == "NPL"))

    return df


def validate_deposit_positions(df):
    """Business rules for deposit_positions raw table."""
    df = df.withColumn("_dq_pass", F.lit(True))

    df = df.withColumn("_dq_pass",
        F.when(F.col("balance") < 0, F.lit(False))
         .otherwise(F.col("_dq_pass")))

    valid_types = ["CASA_Current", "CASA_Saving", "FD", "CD", "Notice"]
    df = df.withColumn("_dq_pass",
        F.when(~F.col("deposit_type").isin(valid_types), F.lit(False))
         .otherwise(F.col("_dq_pass")))

    # Derive CASA flag
    df = df.withColumn("is_casa",
        F.col("deposit_type").isin(["CASA_Current", "CASA_Saving"]))

    return df


def validate_income_statement(df):
    """Business rules for income_statement raw table."""
    df = df.withColumn("_dq_pass", F.lit(True))

    valid_categories = ["Income", "Expense", "Provision", "Tax"]
    df = df.withColumn("_dq_pass",
        F.when(~F.col("category").isin(valid_categories), F.lit(False))
         .otherwise(F.col("_dq_pass")))

    # Income should be positive, expenses negative (or use sign convention)
    # Flag nulls on amount
    df = df.withColumn("_dq_pass",
        F.when(F.col("amount").isNull(), F.lit(False))
         .otherwise(F.col("_dq_pass")))

    return df


def validate_balance_sheet(df):
    """Business rules for balance_sheet raw table."""
    df = df.withColumn("_dq_pass", F.lit(True))

    valid_types = ["Asset", "Liability", "Equity"]
    df = df.withColumn("_dq_pass",
        F.when(~F.col("account_type").isin(valid_types), F.lit(False))
         .otherwise(F.col("_dq_pass")))

    df = df.withColumn("_dq_pass",
        F.when(F.col("balance").isNull(), F.lit(False))
         .otherwise(F.col("_dq_pass")))

    return df


# ── Domain processing map ──────────────────────────────────────────────────────
DOMAIN_CONFIG = {
    "nim": {
        "tables": ["loan_positions", "deposit_positions"],
        "validators": {
            "loan_positions": validate_loan_positions,
            "deposit_positions": validate_deposit_positions,
        },
    },
    "npl_ratio": {
        "tables": ["loan_positions"],
        "validators": {"loan_positions": validate_loan_positions},
    },
    "casa_ratio": {
        "tables": ["deposit_positions"],
        "validators": {"deposit_positions": validate_deposit_positions},
    },
    "roe_roa": {
        "tables": ["income_statement", "balance_sheet"],
        "validators": {
            "income_statement": validate_income_statement,
            "balance_sheet": validate_balance_sheet,
        },
    },
    "cost_income": {
        "tables": ["income_statement"],
        "validators": {"income_statement": validate_income_statement},
    },
    "lcr_nsfr": {
        "tables": ["balance_sheet", "deposit_positions", "loan_positions"],
        "validators": {
            "balance_sheet": validate_balance_sheet,
            "deposit_positions": validate_deposit_positions,
            "loan_positions": validate_loan_positions,
        },
    },
}

# ── Main ETL loop ──────────────────────────────────────────────────────────────
year  = RUN_DATE.strftime("%Y")
month = RUN_DATE.strftime("%m")
day   = RUN_DATE.strftime("%d")

processed_counts = {}

for domain, config in DOMAIN_CONFIG.items():
    for table in config["tables"]:
        source_path = (
            f"s3://{SOURCE_BUCKET}/raw/{domain}/{year}/{month}/{day}/{table}/"
        )
        target_path = (
            f"s3://{TARGET_BUCKET}/curated/{domain}/{table}/"
        )

        logger.info(f"Processing {domain}/{table} from {source_path}")

        try:
            dyf = glueContext.create_dynamic_frame.from_options(
                connection_type="s3",
                connection_options={"paths": [source_path], "recurse": True},
                format="parquet",
                transformation_ctx=f"src_{domain}_{table}",
            )

            if dyf.count() == 0:
                logger.warning(f"No data found for {domain}/{table} — skipping")
                continue

            df = dyf.toDF()

            # Add processing metadata
            df = add_validation_columns(df, domain)

            # Run domain-specific validation
            if table in config["validators"]:
                df = config["validators"][table](df)
            else:
                df = df.withColumn("_dq_pass", F.lit(True))

            # Partition columns
            df = df.withColumn("year",  F.lit(int(year)))
            df = df.withColumn("month", F.lit(int(month)))
            df = df.withColumn("day",   F.lit(int(day)))

            # Write passing records to curated zone
            valid_df = df.filter(F.col("_dq_pass") == True)
            invalid_df = df.filter(F.col("_dq_pass") == False)

            passing_count = valid_df.count()
            failing_count = invalid_df.count()
            processed_counts[f"{domain}/{table}"] = {
                "pass": passing_count,
                "fail": failing_count,
            }

            logger.info(
                f"{domain}/{table}: {passing_count} valid, "
                f"{failing_count} failed DQ"
            )

            # Write valid Parquet (partitioned)
            valid_df.write \
                .mode("overwrite") \
                .partitionBy("year", "month", "day") \
                .parquet(target_path)

            # Write failed records to quarantine path for review
            if failing_count > 0:
                quarantine_path = (
                    f"s3://{TARGET_BUCKET}/quarantine/{domain}/{table}/"
                    f"{year}/{month}/{day}/"
                )
                invalid_df.write \
                    .mode("overwrite") \
                    .parquet(quarantine_path)
                logger.warning(
                    f"  {failing_count} records written to quarantine: "
                    f"{quarantine_path}"
                )

        except Exception as e:
            logger.error(f"Failed processing {domain}/{table}: {e}")
            # Don't fail the whole job — log and continue
            processed_counts[f"{domain}/{table}"] = {"error": str(e)}

# ── Summary log ───────────────────────────────────────────────────────────────
logger.info("=== ETL Summary ===")
for key, counts in processed_counts.items():
    logger.info(f"  {key}: {counts}")

job.commit()
