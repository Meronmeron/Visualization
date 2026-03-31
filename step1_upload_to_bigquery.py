"""
STEP 1 — Upload GB, EU, and US data to BigQuery via AWS S3
==============================================================
This script:
  1. Uploads your CSV files to AWS S3 (ipm-financial-data bucket via EC2 IAM Role)
  2. Creates a BigQuery dataset
  3. Loads the CSVs into BigQuery tables directly

All dependencies are pre-installed in your venv.
GCP credentials are loaded automatically from the service account key on disk.
"""

import boto3
import os
import sys
from google.cloud import bigquery

# ─────────────────────────────────────────────────────────────────
# Auto-configure GCP credentials from the service account key
# ─────────────────────────────────────────────────────────────────
_KEY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "financial-data-491415-ecf1b9ff514d.json"
)
if os.path.exists(_KEY_FILE):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _KEY_FILE
    print(f"🔑 Using GCP key: {_KEY_FILE}")
else:
    print("⚠️  GCP key file not found. Ensure GOOGLE_APPLICATION_CREDENTIALS is set.")


# ─────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────

# AWS S3 — already available via EC2 IAM role (no keys needed)
S3_BUCKET      = "ipm-financial-data"          # Your existing S3 bucket
S3_PREFIX      = "financial_data_exports"       # Folder prefix inside the bucket
AWS_REGION     = "us-east-1"                   # AWS region of the bucket

# Google BigQuery
GCP_PROJECT_ID = "financial-data-491415"        # Your GCP project
DATASET_ID     = "financial_data"               # BigQuery dataset name

# Local file paths on this instance
EXPORTS_DIR    = "/home/meron/pfif_pathway/exports"

FILES = {
    "gb_xbrl": {
        "local_path": os.path.join(EXPORTS_DIR, "GB_XBRL_filings_long.csv"),
        "s3_key":     f"{S3_PREFIX}/gb_xbrl_raw.csv",
        "table":      "gb_xbrl_raw",
        "schema": [
            bigquery.SchemaField("company_name", "STRING"),
            bigquery.SchemaField("country",      "STRING"),
            bigquery.SchemaField("unit",         "STRING"),
            bigquery.SchemaField("concept",      "STRING"),
            bigquery.SchemaField("value",        "STRING"),   # Keep as STRING; cast in SQL
            bigquery.SchemaField("period",       "STRING"),
            bigquery.SchemaField("period_end",   "STRING"),   # Cast to DATE in SQL
            bigquery.SchemaField("filing_date",  "STRING"),
            bigquery.SchemaField("decimals",     "STRING"),
        ]
    },
    "eu_xbrl": {
        "local_path": os.path.join(EXPORTS_DIR, "EU_data.csv"),
        "s3_key":     f"{S3_PREFIX}/eu_xbrl_raw.csv",
        "table":      "eu_xbrl_raw",
        "schema": [
            bigquery.SchemaField("company_name", "STRING"),
            bigquery.SchemaField("country",      "STRING"),
            bigquery.SchemaField("unit",         "STRING"),
            bigquery.SchemaField("concept",      "STRING"),
            bigquery.SchemaField("value",        "STRING"),
            bigquery.SchemaField("period",       "STRING"),
            bigquery.SchemaField("period_end",   "STRING"),
            bigquery.SchemaField("filing_date",  "STRING"),
            bigquery.SchemaField("decimals",     "STRING"),
        ]
    },
    "us_edgar": {
        "local_path": os.path.join(EXPORTS_DIR, "russell1000_edgar_filtered.csv"), # Using filtered file for reliability
        "s3_key":     f"{S3_PREFIX}/us_edgar_raw.csv",
        "table":      "us_edgar_raw",
        "schema": [
            bigquery.SchemaField("company_name",  "STRING"),
            bigquery.SchemaField("country",       "STRING"),
            bigquery.SchemaField("unit",          "STRING"),
            bigquery.SchemaField("concept",       "STRING"),
            bigquery.SchemaField("value",         "STRING"),
            bigquery.SchemaField("period",        "STRING"),
            bigquery.SchemaField("period_end",    "STRING"),
            bigquery.SchemaField("filing_date",   "STRING"),
            bigquery.SchemaField("cik",           "STRING"),
            bigquery.SchemaField("sic",           "STRING"),
            bigquery.SchemaField("form",          "STRING"),
            bigquery.SchemaField("fiscal_year",   "STRING"),
            bigquery.SchemaField("fiscal_period", "STRING"),
            bigquery.SchemaField("qtrs",          "STRING"),
            bigquery.SchemaField("coreg",         "STRING"),
            bigquery.SchemaField("source_quarter","STRING"),
        ]
    }
}


# ─────────────────────────────────────────────────────────────────
# STEP 1A — Create BigQuery Dataset
# ─────────────────────────────────────────────────────────────────
def create_bq_dataset(bq_client):
    """Creates the BigQuery dataset if it does not exist.
    If the service account lacks create permission, assumes it already exists and continues.
    """
    dataset_ref = f"{GCP_PROJECT_ID}.{DATASET_ID}"
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US"
    try:
        bq_client.create_dataset(dataset, exists_ok=True)
        print(f"✅ BigQuery dataset '{DATASET_ID}' ready in project '{GCP_PROJECT_ID}'")
    except Exception as e:
        if "403" in str(e) or "Access Denied" in str(e) or "already exists" in str(e).lower():
            print(f"ℹ️  Dataset '{DATASET_ID}' assumed to already exist (no create permission, continuing...)")
        else:
            print(f"❌ Failed to create dataset: {e}")
            sys.exit(1)


# ─────────────────────────────────────────────────────────────────
# STEP 1B — Upload CSV to AWS S3
# ─────────────────────────────────────────────────────────────────
def upload_to_s3(local_path, s3_key):
    """
    Uploads a file to S3. Uses the EC2 IAM role automatically —
    no access keys required.
    """
    if not os.path.exists(local_path):
        print(f"   ⚠️  File not found: {local_path}  — skipping")
        return None

    s3 = boto3.client("s3", region_name=AWS_REGION)
    file_size_gb = os.path.getsize(local_path) / (1024 ** 3)

    print(f"   ⏳ Uploading {os.path.basename(local_path)} ({file_size_gb:.2f} GB) → s3://{S3_BUCKET}/{s3_key}")

    # Use multipart upload for large files (>100 MB) for speed
    from boto3.s3.transfer import TransferConfig
    config = TransferConfig(
        multipart_threshold=100 * 1024 * 1024,   # 100 MB threshold
        max_concurrency=10,
        multipart_chunksize=100 * 1024 * 1024,
        use_threads=True
    )

    try:
        s3.upload_file(local_path, S3_BUCKET, s3_key, Config=config)
        s3_uri = f"s3://{S3_BUCKET}/{s3_key}"
        print(f"   ✅ Uploaded to {s3_uri}")
        return s3_uri
    except Exception as e:
        print(f"   ❌ S3 upload failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────
# STEP 1C — Load from S3 into BigQuery
# ─────────────────────────────────────────────────────────────────
def load_s3_to_bigquery(bq_client, s3_uri, table_id, schema):
    """
    BigQuery can load directly from S3 using an external connection,
    OR we use the GCS-compatible approach via a Transfer from S3→GCS→BQ.

    The simplest reliable approach: download from S3, upload to BQ directly
    using the local file (already on disk). This avoids needing to set up
    a BigQuery-S3 external connection.

    NOTE: If you want to load directly from S3 → BigQuery without a local copy,
    you need to set up a BigQuery Omni connection in your GCP project.
    See: https://cloud.google.com/bigquery/docs/omni-aws-introduction
    """
    full_table_id = f"{GCP_PROJECT_ID}.{DATASET_ID}.{table_id}"

    # Find the local file that was already uploaded to S3
    local_path = None
    for cfg in FILES.values():
        if cfg["table"] == table_id:
            local_path = cfg["local_path"]
            break

    if not local_path or not os.path.exists(local_path):
        print(f"   ⚠️  Local file for '{table_id}' not found. Skipping BQ load.")
        return

    print(f"   ⏳ Loading into BigQuery: {full_table_id}")

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
        ignore_unknown_values=True,
        max_bad_records=1000,
    )

    try:
        with open(local_path, "rb") as f:
            load_job = bq_client.load_table_from_file(f, full_table_id, job_config=job_config)
            load_job.result()  # Wait for completion

        table = bq_client.get_table(full_table_id)
        print(f"   ✅ Loaded {table.num_rows:,} rows into {full_table_id}")
    except Exception as e:
        print(f"   ❌ BigQuery load failed: {e}")


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 65)
    print("  Pipeline: AWS S3 Upload + BigQuery Load")
    print("  GB XBRL | EU XBRL | US Russell 1000 (EDGAR)")
    print("=" * 65)

    bq_client = bigquery.Client(project=GCP_PROJECT_ID)

    # Step 1A: Create dataset
    create_bq_dataset(bq_client)

    # Step 1B + 1C: Upload to S3, then load into BigQuery
    for source_name, cfg in FILES.items():
        print(f"\n📂  Processing: {source_name.upper()}")

        # 1B. Upload to S3 (for archiving and potential BigQuery Omni use)
        s3_uri = upload_to_s3(cfg["local_path"], cfg["s3_key"])

        # 1C. Load directly into BigQuery from local file
        load_s3_to_bigquery(bq_client, s3_uri, cfg["table"], cfg["schema"])

    print("\n🎉 All done!")
    print(f"   BigQuery: https://console.cloud.google.com/bigquery?project={GCP_PROJECT_ID}")
    print(f"   S3:       https://s3.console.aws.amazon.com/s3/buckets/{S3_BUCKET}")
    print(f"\n👉 NEXT STEP: Run step2_bigquery_queries.sql in the BigQuery SQL Editor")
