"""
DAG Airflow : récupère chaque jour les taux de change (API Frankfurter v2)
et les charge dans BigQuery, dataset `raw`, table `taux_change`.

Pour reprendre plusieurs années d'historique en une seule fois, voir le DAG
`backfill_forex_history`.

Pré-requis :
- Connexion Airflow `google_cloud_default` configurée avec la clé du
  service account.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from frankfurter import fetch_rates, load_to_bigquery

default_args = {
    "owner": "cedeao-remitflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def fetch_and_load(**context):
    rows = fetch_rates()
    n = load_to_bigquery(rows)
    print(f"{n} taux chargés dans raw.taux_change")


with DAG(
    dag_id="ingest_forex_rates",
    description="Récupération quotidienne des taux de change EUR -> NGN/GHS/USD/XOF",
    default_args=default_args,
    schedule_interval="0 7 * * *",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=["remitflow", "forex"],
) as dag:
    ingest_task = PythonOperator(
        task_id="fetch_and_load_forex_rates",
        python_callable=fetch_and_load,
    )
