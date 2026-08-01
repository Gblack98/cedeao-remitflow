"""Charge les données brutes dans BigQuery sans passer par Airflow.

Reprend la logique exacte des DAGs — fetch_rates pour les taux,
generate_one pour les transferts — avec les mêmes schémas explicites.
Sert à amorcer l'entrepôt ou à le reconstruire avant une démonstration,
quand faire tourner un ordonnanceur complet n'a pas d'intérêt.

Usage :
    python scripts/load_raw_data.py --debut 2024-01-01 --transferts 20000
"""

import argparse
import os
import random
import sys
from datetime import datetime

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "airflow", "dags"))
sys.path.insert(0, os.path.join(RACINE, "generator"))

from frankfurter import fetch_rates  # noqa: E402
from generate_transfers import generate_one  # noqa: E402
from bq_schemas import SCHEMA_TAUX, SCHEMA_TRANSFERTS  # noqa: E402

from google.cloud import bigquery  # noqa: E402
from google.oauth2 import service_account  # noqa: E402


def assurer_dataset(client, projet, nom="raw", location="EU"):
    """Crée le dataset s'il n'existe pas — les tables Sandbox expirent au
    bout de 60 jours, une reconstruction complète doit rester possible."""
    ref = bigquery.Dataset(f"{projet}.{nom}")
    ref.location = location
    client.create_dataset(ref, exists_ok=True)


def charger(client, projet, rows, table, schema):
    cfg = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=schema,
    )
    client.load_table_from_json(rows, f"{projet}.raw.{table}", job_config=cfg).result()
    print(f"  raw.{table} : {client.get_table(f'{projet}.raw.{table}').num_rows} lignes")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--projet", default=os.environ.get("REMITFLOW_PROJECT", "crucial-bonsai-418120"))
    p.add_argument("--keyfile", default=os.environ.get("REMITFLOW_KEYFILE", "~/.gcp/remitflow-sa.json"))
    p.add_argument("--debut", default="2024-01-01")
    p.add_argument("--fin", default=datetime.utcnow().strftime("%Y-%m-%d"))
    p.add_argument("--transferts", type=int, default=20000)
    args = p.parse_args()

    creds = service_account.Credentials.from_service_account_file(
        os.path.expanduser(args.keyfile)
    )
    client = bigquery.Client(project=args.projet, credentials=creds)
    assurer_dataset(client, args.projet)

    print(f"Taux de change {args.debut} -> {args.fin}")
    taux = fetch_rates(debut=args.debut, fin=args.fin)
    charger(client, args.projet, taux, "taux_change", SCHEMA_TAUX)

    print(f"Transferts simulés ({args.transferts})")
    dates = sorted({r["date_taux"] for r in taux})
    # Graine fixe : deux exécutions produisent le même jeu, ce qui rend
    # les chiffres du rapport reproductibles.
    random.seed(42)
    rows = [
        generate_one(datetime.strptime(random.choice(dates), "%Y-%m-%d"))
        for _ in range(args.transferts)
    ]
    charger(client, args.projet, rows, "transferts", SCHEMA_TRANSFERTS)


if __name__ == "__main__":
    main()
