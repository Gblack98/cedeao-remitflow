"""
DAG Airflow : reprise de l'historique des taux de change.

L'API Frankfurter v2 expose des séries quotidiennes remontant à 1999 pour
le Naira et à 2007 pour le Cedi. Ce DAG récupère une plage complète en un
appel, ce qui évite d'attendre que le DAG quotidien accumule assez de
points pour analyser la volatilité.

Déclenchement manuel uniquement. La plage est paramétrable au lancement
(« Trigger DAG w/ config ») :

    {"debut": "2024-01-01", "fin": "2026-07-30"}

Le chargement écrase la table (`WRITE_TRUNCATE`) : la reprise reconstruit
l'historique complet plutôt que de s'ajouter à l'existant, ce qui évite les
doublons si le DAG est relancé.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from frankfurter import fetch_rates, load_to_bigquery

DEBUT_PAR_DEFAUT = "2024-01-01"

default_args = {
    "owner": "cedeao-remitflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def backfill(**context):
    conf = context["dag_run"].conf or {}
    debut = conf.get("debut", DEBUT_PAR_DEFAUT)
    fin = conf.get("fin", datetime.utcnow().strftime("%Y-%m-%d"))

    rows = fetch_rates(debut=debut, fin=fin)
    n = load_to_bigquery(rows, write_disposition="WRITE_TRUNCATE")
    print(f"{n} taux chargés pour la période {debut} -> {fin}")


with DAG(
    dag_id="backfill_forex_history",
    description="Reprise de l'historique des taux de change sur une plage de dates",
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=["remitflow", "forex", "backfill"],
) as dag:
    backfill_task = PythonOperator(
        task_id="backfill_forex_rates",
        python_callable=backfill,
    )
