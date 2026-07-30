"""
DAG Airflow : récupère chaque jour les taux de change (API Frankfurter) et
les charge dans BigQuery, dataset `raw`, table `taux_change`.

Le chargement passe par un load job (`load_table_from_json`) et non par un
insert streaming (`insert_rows_json`) : le mode BigQuery Sandbox ne
supporte pas les streaming inserts, seuls les batch load jobs fonctionnent.

Pré-requis :
- Connexion Airflow `google_cloud_default` configurée avec la clé du
  service account (voir docs/ROADMAP.md, section configuration).
"""

from datetime import datetime, timedelta, timezone

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
from google.cloud import bigquery

FRANKFURTER_URL = "https://api.frankfurter.dev/v2/latest"
DEVISES_CIBLES = ["NGN", "GHS", "USD"]

# Le XOF est arrimé à taux fixe à l'euro (1 EUR = 655.957 XOF, accord de
# coopération monétaire UEMOA/France) : ce n'est pas une donnée à récupérer
# via API, c'est une constante réglementaire qu'on documente ici.
XOF_PER_EUR = 655.957

default_args = {
    "owner": "cedeao-remitflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def fetch_and_load(**context):
    resp = requests.get(
        FRANKFURTER_URL,
        params={"base": "EUR", "symbols": ",".join(DEVISES_CIBLES)},
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()

    now_iso = datetime.now(timezone.utc).isoformat()

    rows = [
        {
            "date_taux": payload["date"],
            "devise_base": "EUR",
            "devise_cible": devise,
            "taux": rate,
            "recupere_le": now_iso,
        }
        for devise, rate in payload["rates"].items()
    ]

    # parité fixe XOF, ajoutée manuellement à chaque run
    rows.append({
        "date_taux": payload["date"],
        "devise_base": "EUR",
        "devise_cible": "XOF",
        "taux": XOF_PER_EUR,
        "recupere_le": now_iso,
    })

    hook = BigQueryHook(gcp_conn_id="google_cloud_default", use_legacy_sql=False)
    client = hook.get_client()
    table_id = f"{hook.project_id}.raw.taux_change"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
    )
    load_job = client.load_table_from_json(rows, table_id, job_config=job_config)
    load_job.result()  # attend la fin du job, lève une exception si échec


with DAG(
    dag_id="ingest_forex_rates",
    description="Récupération quotidienne des taux de change EUR -> NGN/GHS/XOF",
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
