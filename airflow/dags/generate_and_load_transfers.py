"""
DAG Airflow : génère un lot de transferts simulés et les charge en mode
batch dans BigQuery, dataset `raw`, table `transferts`.

Tourne plusieurs fois par jour plutôt qu'en flux continu pendant une
démo : plus simple à piloter et à déboguer, et de toute façon compatible
avec les limites du mode BigQuery Sandbox (pas de streaming insert, voir
`ingest_forex_rates.py` pour le même choix côté taux de change).
"""

import os
import sys
from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
from google.cloud import bigquery

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "generator"))
from generate_transfers import generate_one  # noqa: E402

N_PAR_LOT = 200

default_args = {
    "owner": "cedeao-remitflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def generate_and_load(**context):
    now = datetime.now(timezone.utc)
    rows = [generate_one(now) for _ in range(N_PAR_LOT)]

    hook = BigQueryHook(gcp_conn_id="google_cloud_default", use_legacy_sql=False)
    client = hook.get_client()
    table_id = f"{hook.project_id}.raw.transferts"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
    )
    load_job = client.load_table_from_json(rows, table_id, job_config=job_config)
    load_job.result()


with DAG(
    dag_id="generate_and_load_transfers",
    description="Génération et chargement batch de transferts simulés",
    default_args=default_args,
    schedule_interval="0 */4 * * *",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=["remitflow", "transferts"],
) as dag:
    generate_task = PythonOperator(
        task_id="generate_and_load_batch",
        python_callable=generate_and_load,
    )
