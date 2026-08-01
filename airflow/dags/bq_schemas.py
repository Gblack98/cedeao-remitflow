"""Schémas des tables brutes BigQuery.

Définis une seule fois et partagés par les DAGs et le script de
chargement : deux définitions divergentes provoquent un rejet au
chargement, la table gardant le type de la première écriture.

L'autodétection est écartée volontairement. Elle déduit le type du
premier lot reçu — `heure_transfert` vaut "12:36:22", que BigQuery
interprète comme un TIME alors que la colonne est un STRING — et fait
échouer tout chargement ultérieur avec un schéma différent.
"""

from google.cloud import bigquery

SCHEMA_TAUX = [
    bigquery.SchemaField("date_taux", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("devise_base", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("devise_cible", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("taux", "NUMERIC", mode="REQUIRED"),
    bigquery.SchemaField("recupere_le", "TIMESTAMP", mode="REQUIRED"),
]

SCHEMA_TRANSFERTS = [
    bigquery.SchemaField("transfert_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("date_transfert", "DATE", mode="REQUIRED"),
    # STRING et non TIME : l'heure n'est pas un axe d'analyse du projet,
    # et la conserver telle que produite évite une conversion inutile.
    bigquery.SchemaField("heure_transfert", "STRING"),
    bigquery.SchemaField("pays_source", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("pays_cible", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("devise_source", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("devise_cible", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("canal", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("montant_source_xof", "NUMERIC", mode="REQUIRED"),
    bigquery.SchemaField("frais_transaction_xof", "NUMERIC", mode="REQUIRED"),
    bigquery.SchemaField("statut", "STRING", mode="REQUIRED"),
]
