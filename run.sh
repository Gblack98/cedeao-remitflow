#!/usr/bin/env bash
#
# Lance le projet de bout en bout : dépendances, profil dbt, chargement
# des données brutes, transformations, tests, puis dashboard.
#
#   ./run.sh                  tout, du début au dashboard
#   ./run.sh --skip-load      sans recharger les données brutes
#   ./run.sh --skip-dbt       sans reconstruire les modèles
#   ./run.sh --no-dashboard   s'arrête après les tests dbt
#
# Prérequis : une clé de compte de service BigQuery. Par défaut
# ~/.gcp/remitflow-sa.json, sinon REMITFLOW_KEYFILE.

set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RACINE"

PROJET="${REMITFLOW_PROJECT:-crucial-bonsai-418120}"
DATASET="${REMITFLOW_DATASET:-dbt_dev_gabar}"
KEYFILE="${REMITFLOW_KEYFILE:-$HOME/.gcp/remitflow-sa.json}"
DEBUT="${REMITFLOW_DEBUT:-2024-01-01}"
NB_TRANSFERTS="${REMITFLOW_TRANSFERTS:-20000}"

SKIP_LOAD=0; SKIP_DBT=0; DASHBOARD=1
for arg in "$@"; do
  case "$arg" in
    --skip-load)    SKIP_LOAD=1 ;;
    --skip-dbt)     SKIP_DBT=1 ;;
    --no-dashboard) DASHBOARD=0 ;;
    -h|--help)      sed -n '3,13p' "$0"; exit 0 ;;
    *) echo "option inconnue : $arg" >&2; exit 2 ;;
  esac
done

etape() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

# --- 1. Dépendances ---------------------------------------------------
etape "Dépendances"
command -v python3 >/dev/null || { echo "python3 introuvable" >&2; exit 1; }

if [ ! -d venv ]; then
  echo "création de l'environnement virtuel"
  python3 -m venv venv
fi
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt
echo "environnement prêt : $(./venv/bin/python --version)"

# --- 2. Identifiants --------------------------------------------------
etape "Identifiants BigQuery"
if [ ! -f "$KEYFILE" ]; then
  cat >&2 <<EOF
Clé de compte de service introuvable : $KEYFILE

Créer le compte de service et sa clé :
  gcloud iam service-accounts create remitflow-dbt --project=$PROJET
  gcloud projects add-iam-policy-binding $PROJET \\
    --member="serviceAccount:remitflow-dbt@$PROJET.iam.gserviceaccount.com" \\
    --role=roles/bigquery.dataEditor
  gcloud projects add-iam-policy-binding $PROJET \\
    --member="serviceAccount:remitflow-dbt@$PROJET.iam.gserviceaccount.com" \\
    --role=roles/bigquery.jobUser
  mkdir -p ~/.gcp && gcloud iam service-accounts keys create $KEYFILE \\
    --iam-account=remitflow-dbt@$PROJET.iam.gserviceaccount.com
EOF
  exit 1
fi
echo "clé trouvée : $KEYFILE"

# --- 3. Profil dbt ----------------------------------------------------
etape "Profil dbt"
PROFILES="$HOME/.dbt/profiles.yml"
mkdir -p "$HOME/.dbt"
if [ -f "$PROFILES" ] && grep -q '^cedeao_remitflow:' "$PROFILES"; then
  echo "profil cedeao_remitflow déjà présent, inchangé"
else
  # Ajout en fin de fichier : les profils d'autres projets sont conservés.
  [ -f "$PROFILES" ] && cp "$PROFILES" "$PROFILES.bak-$(date +%s)"
  cat >> "$PROFILES" <<EOF

cedeao_remitflow:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: $PROJET
      dataset: $DATASET
      keyfile: $KEYFILE
      threads: 4
      location: EU
EOF
  echo "profil cedeao_remitflow ajouté à $PROFILES"
fi

# --- 4. Données brutes ------------------------------------------------
if [ "$SKIP_LOAD" -eq 0 ]; then
  etape "Chargement des données brutes"
  REMITFLOW_PROJECT="$PROJET" REMITFLOW_KEYFILE="$KEYFILE" \
    ./venv/bin/python scripts/load_raw_data.py \
      --debut "$DEBUT" --transferts "$NB_TRANSFERTS"
else
  etape "Chargement ignoré (--skip-load)"
fi

# --- 5. Transformations et tests --------------------------------------
if [ "$SKIP_DBT" -eq 0 ]; then
  etape "Modèles dbt et tests"
  (cd dbt && "$RACINE/venv/bin/dbt" build)
else
  etape "dbt ignoré (--skip-dbt)"
fi

# --- 6. Dashboard -----------------------------------------------------
if [ "$DASHBOARD" -eq 1 ]; then
  etape "Dashboard"
  echo "http://localhost:8501 — Ctrl+C pour arrêter"
  REMITFLOW_PROJECT="$PROJET" REMITFLOW_DATASET="$DATASET" \
  REMITFLOW_KEYFILE="$KEYFILE" \
    ./venv/bin/streamlit run dashboard/app.py
else
  etape "Terminé"
fi
