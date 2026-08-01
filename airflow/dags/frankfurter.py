"""
Client de l'API Frankfurter (v2) et chargement des taux dans BigQuery.

Logique partagée entre le DAG quotidien (`ingest_forex_rates`) et le DAG de
reprise d'historique (`backfill_forex_history`).

L'endpoint v2 est `/v2/rates`. Il attend le paramètre `quotes` (et non
`symbols`, qui renvoie une erreur 422) et répond par une liste plate
d'enregistrements, un par couple date/devise :

    [{"date": "2026-07-30", "base": "EUR", "quote": "NGN", "rate": 1558.14}, ...]

Le module n'importe rien d'Airflow au niveau global : il reste utilisable
et testable en dehors d'un ordonnanceur.
"""

from datetime import datetime, timezone

import requests

RATES_URL = "https://api.frankfurter.dev/v2/rates"

# Devises récupérées via l'API. Le XOF en est volontairement exclu : voir
# XOF_PER_EUR ci-dessous.
DEVISES_CIBLES = ["NGN", "GHS", "USD"]

# Le XOF est arrimé à taux fixe à l'euro (accord de coopération monétaire
# UEMOA/France). L'API expose bien la devise, mais arrondie à 655,96 ; la
# valeur réglementaire exacte est plus précise, donc nous l'injectons
# nous-mêmes pour chaque date observée.
XOF_PER_EUR = 655.957

TIMEOUT = 30


def fetch_rates(date=None, debut=None, fin=None, group=None):
    """Récupère les taux EUR -> devises cibles, avec le XOF ajouté.

    Sans argument, renvoie les taux les plus récents. `debut`/`fin`
    délimitent une plage de dates (format YYYY-MM-DD) ; `group` permet de
    sous-échantillonner une plage ("month", par exemple).
    """
    params = {"base": "EUR", "quotes": ",".join(DEVISES_CIBLES)}
    if date:
        params["date"] = date
    if debut:
        params["from"] = debut
    if fin:
        params["to"] = fin
    if group:
        params["group"] = group

    resp = requests.get(RATES_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()

    recupere_le = datetime.now(timezone.utc).isoformat()

    rows = [
        {
            "date_taux": r["date"],
            "devise_base": r["base"],
            "devise_cible": r["quote"],
            "taux": r["rate"],
            "recupere_le": recupere_le,
        }
        for r in payload
    ]

    # Une ligne XOF par date effectivement présente dans la réponse. Les
    # dates peuvent différer d'une devise à l'autre selon les jours de
    # publication, d'où le passage par l'ensemble des dates observées.
    for jour in sorted({r["date_taux"] for r in rows}):
        rows.append({
            "date_taux": jour,
            "devise_base": "EUR",
            "devise_cible": "XOF",
            "taux": XOF_PER_EUR,
            "recupere_le": recupere_le,
        })

    return rows


def load_to_bigquery(rows, write_disposition="WRITE_APPEND"):
    """Charge les lignes dans `raw.taux_change` via un batch load job.

    Le mode BigQuery Sandbox ne supporte pas les insertions en streaming :
    seuls les load jobs fonctionnent.
    """
    from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
    from google.cloud import bigquery

    from bq_schemas import SCHEMA_TAUX

    if not rows:
        raise ValueError("aucun taux à charger : réponse de l'API vide")

    hook = BigQueryHook(gcp_conn_id="google_cloud_default", use_legacy_sql=False)
    client = hook.get_client()
    table_id = f"{hook.project_id}.raw.taux_change"

    job_config = bigquery.LoadJobConfig(
        write_disposition=write_disposition,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=SCHEMA_TAUX,
    )
    load_job = client.load_table_from_json(rows, table_id, job_config=job_config)
    load_job.result()  # attend la fin du job, lève une exception si échec

    return len(rows)
