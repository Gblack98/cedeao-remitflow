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

Airflow (orchestration) · BigQuery Sandbox (entrepôt) · dbt Core (transformation et tests) · Looker Studio (dashboard).

Le dashboard s'appuie sur `obt_transferts`, table dénormalisée dérivée du schéma en étoile.

## Lancement

```bash
./run.sh
```

Installe les dépendances, configure le profil dbt, charge les données brutes,
construit les modèles, exécute les tests et ouvre le dashboard sur
http://localhost:8501.

Options : `--avec-airflow`, `--skip-load`, `--skip-dbt`, `--no-dashboard`.

Prérequis : une clé de compte de service BigQuery dans `~/.gcp/remitflow-sa.json`
(ou `REMITFLOW_KEYFILE`). Le script indique les commandes de création si elle manque.

### Avec l'orchestrateur

```bash
./run.sh --avec-airflow
```

Installe Airflow au passage s'il manque, crée sa connexion BigQuery, puis exécute
les trois DAGs avant de reconstruire les modèles.

Airflow vit dans un environnement virtuel distinct (`requirements-airflow.txt`) :
il épingle des versions de `google-cloud-*` et de `protobuf` incompatibles avec
dbt dans un même environnement. `run.sh` s'en occupe, il n'y a rien à installer
à la main.

L'option reste hors du parcours par défaut à dessein. Le chargement de base fixe
sa graine aléatoire, ce qui rend les chiffres du rapport reproductibles d'une
exécution à l'autre ; les DAGs ajoutent à chaque passage un lot de transferts qui
ne l'est pas.

Pour l'interface graphique (captures d'écran, démonstration) :

```bash
./airflow.sh web        # http://localhost:8080
./airflow.sh test       # exécute les trois DAGs sans ordonnanceur
```

Préférer `test` à un ordonnanceur laissé en tâche de fond : interrompre ce
dernier abandonne ses tâches en cours, qui restent affichées en `up_for_retry`
sur un run jamais clôturé — un DAG parfaitement sain paraît alors cassé.

## Structure

```
generator/       simulation des transferts
airflow/dags/    ingestion des taux de change et des transferts
scripts/         chargement des données brutes sans ordonnanceur
dbt/             staging -> intermediate -> marts
dashboard/       tableau de bord Streamlit
docs/schema.md   schéma en étoile
```
