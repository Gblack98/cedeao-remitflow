#!/usr/bin/env bash
#
# Pilote Airflow en local. L'ordonnanceur vit dans un environnement
# virtuel distinct de celui du pipeline : Airflow épingle des versions de
# google-cloud et protobuf incompatibles avec dbt.
#
#   ./airflow.sh init       base de données + connexion BigQuery
#   ./airflow.sh list       DAGs détectés et erreurs d'import
#   ./airflow.sh test       exécute les deux DAGs sans ordonnanceur
#   ./airflow.sh web        interface web sur http://localhost:8080
#   ./airflow.sh <autre>    passe la commande à l'outil airflow
#
# AIRFLOW_HOME est placé dans le projet, pas dans ~/airflow : tout reste
# contenu et supprimable d'un rm -rf airflow_home.

set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RACINE"

export AIRFLOW_HOME="$RACINE/airflow_home"
export AIRFLOW__CORE__DAGS_FOLDER="$RACINE/airflow/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__CORE__EXECUTOR=SequentialExecutor
export AIRFLOW__CORE__PARALLELISM=1

PROJET="${REMITFLOW_PROJECT:-crucial-bonsai-418120}"
KEYFILE="${REMITFLOW_KEYFILE:-$HOME/.gcp/remitflow-sa.json}"
AF="$RACINE/venv-airflow/bin/airflow"

if [ ! -x "$AF" ]; then
  cat >&2 <<EOF
Airflow n'est pas installé. Environnement dédié à créer :

  python3 -m venv venv-airflow
  ./venv-airflow/bin/pip install "apache-airflow==2.9.3" \\
    apache-airflow-providers-google requests faker \\
    --constraint https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.12.txt

Le fichier de contraintes n'est pas optionnel : sans lui, le provider
Google tire une version qui exige Airflow 3.x et casse l'installation.
EOF
  exit 1
fi

CMD="${1:-list}"; shift || true

case "$CMD" in
  init)
    mkdir -p "$AIRFLOW_HOME"
    "$AF" db migrate
    "$AF" connections delete google_cloud_default >/dev/null 2>&1 || true
    "$AF" connections add google_cloud_default \
      --conn-type google_cloud_platform \
      --conn-extra "{\"key_path\": \"$KEYFILE\", \"project\": \"$PROJET\"}"
    echo "base initialisée, connexion google_cloud_default créée"
    ;;

  list)
    "$AF" dags list
    echo
    echo "-- erreurs d'import --"
    "$AF" dags list-import-errors
    ;;

  test)
    # `dags test` exécute le DAG dans le processus courant, sans
    # ordonnanceur ni base de tâches : c'est la façon la plus directe de
    # vérifier qu'un DAG fait réellement ce qu'il annonce.
    HIER="$(date -u -d 'yesterday' +%Y-%m-%d)"
    echo "== ingest_forex_rates =="
    "$AF" dags test ingest_forex_rates "$HIER"
    echo
    echo "== backfill_forex_history =="
    "$AF" dags test backfill_forex_history "$HIER" \
      --conf '{"debut": "2026-01-01"}'
    ;;

  web)
    echo "interface : http://localhost:8080 (identifiants affichés ci-dessous)"
    "$AF" standalone
    ;;

  *)
    "$AF" "$CMD" "$@"
    ;;
esac
