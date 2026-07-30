# CEDEAO-RemitFlow

Pipeline analytics sur les transferts d'argent transfrontaliers en zone CEDEAO.
Master 1 MBDA — UN-CHK, 2026.

## Sujet

Nous suivons les transferts entre la zone UEMOA et le reste de la CEDEAO (Nigeria, Ghana), et mesurons l'effet de la volatilité du Naira et du Cedi sur les montants reçus.

Le XOF est arrimé à taux fixe à l'euro depuis 1999. Un transfert Dakar → Abidjan n'a donc aucun risque de change, un transfert Dakar → Lagos en a un. Le projet compare les deux types de corridors.

## Données

- Taux de change réels, récupérés quotidiennement via l'API Frankfurter.
- Transferts simulés avec Faker, avec des proportions de volume par pays calées sur le Global Findex de la Banque Mondiale.

## Stack

Airflow (orchestration) · BigQuery Sandbox (entrepôt) · dbt Core (transformation et tests) · Grafana Cloud (dashboard).

## Installation

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python generator/generate_transfers.py --n 2000 --output data/test.csv
```

## Structure

```
generator/       simulation des transferts
airflow/dags/    ingestion des taux de change et des transferts
dbt/             staging -> intermediate -> marts
docs/schema.md   schéma en étoile
```
