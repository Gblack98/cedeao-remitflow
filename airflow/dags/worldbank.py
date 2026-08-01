"""
Client de l'API World Bank Indicators (v2) et chargement dans BigQuery.

Deuxième source réelle du projet, à côté de Frankfurter. Elle apporte ce
que les taux de change ne disent pas : combien d'argent circule vraiment
par pays, et combien coûte réellement un envoi.

    https://api.worldbank.org/v2/country/SEN;NGA/indicator/BX.TRF.PWKR.CD.DT?format=json

L'API est publique, sans clé, et renvoie une enveloppe en deux parties :
un objet de pagination, puis la liste des observations.

    [{"page": 1, "pages": 12, ...},
     [{"countryiso3code": "SEN", "date": "2023", "value": 3012...}, ...]]

Un appel ne porte que sur un indicateur : on interroge donc les quatre
indicateurs séparément, puis on les recroise sur le couple (pays, année).

Les valeurs manquantes sont fréquentes et normales — les coûts d'envoi ne
sont publiés que pour les corridors effectivement enquêtés par la Banque
mondiale. Elles restent à NULL plutôt que d'être comblées.

Le module n'importe rien d'Airflow au niveau global : il reste utilisable
et testable en dehors d'un ordonnanceur.
"""

from datetime import datetime, timezone

import requests

BASE_URL = "https://api.worldbank.org/v2/country/{pays}/indicator/{indicateur}"

# Les 8 pays du périmètre, code ISO3 -> libellé utilisé partout ailleurs
# dans le projet (dim_corridor, générateur). Le libellé de l'API diffère
# parfois ("Cote d'Ivoire" vs "Côte d'Ivoire"), on impose donc le nôtre.
PAYS = {
    "SEN": "Senegal",
    "CIV": "Cote d'Ivoire",
    "MLI": "Mali",
    "BFA": "Burkina Faso",
    "BEN": "Benin",
    "TGO": "Togo",
    "NGA": "Nigeria",
    "GHA": "Ghana",
}

# Indicateur World Bank -> colonne de raw.wb_remittances.
INDICATEURS = {
    "BX.TRF.PWKR.CD.DT": "remises_recues_usd",
    "BM.TRF.PWKR.CD.DT": "remises_envoyees_usd",
    # "IB" = inbound : coût moyen d'un envoi *vers* le pays.
    "SI.RMT.COST.IB.ZS": "cout_envoi_vers_pct",
    # "OB" = outbound : coût moyen d'un envoi *depuis* le pays. Bien plus
    # lacunaire que le précédent (3 pays sur 8 renseignés).
    "SI.RMT.COST.OB.ZS": "cout_envoi_depuis_pct",
}

ANNEE_DEBUT = 2010
# L'API répond en 30 à 40 secondes sur ces requêtes multi-pays : un
# timeout court la ferait échouer alors qu'elle fonctionne.
TIMEOUT = 90
# 8 pays x 17 ans = 136 lignes par indicateur, une seule page suffit.
# Plafonné à 500 : au-delà, l'API répond 400 au lieu de tronquer.
PER_PAGE = 500


def _fetch_indicateur(indicateur, debut, fin):
    """Renvoie {(iso3, annee): valeur} pour un indicateur donné."""
    url = BASE_URL.format(pays=";".join(PAYS), indicateur=indicateur)
    params = {"format": "json", "date": f"{debut}:{fin}", "per_page": PER_PAGE}

    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()

    # Une requête mal formée répond 200 avec un message d'erreur en
    # première position au lieu de l'enveloppe de pagination habituelle.
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        raise ValueError(f"réponse inattendue pour {indicateur} : {payload}")

    return {
        (r["countryiso3code"], int(r["date"])): r["value"]
        for r in payload[1]
        if r["value"] is not None
    }


def fetch_remittances(debut=ANNEE_DEBUT, fin=None):
    """Récupère les 4 indicateurs et les recroise par (pays, année).

    Une ligne = un pays pour une année. Les années sans aucune donnée sur
    les 4 indicateurs sont écartées.
    """
    fin = fin or datetime.now(timezone.utc).year
    par_indicateur = {
        colonne: _fetch_indicateur(indicateur, debut, fin)
        for indicateur, colonne in INDICATEURS.items()
    }

    recupere_le = datetime.now(timezone.utc).isoformat()
    rows = []
    for iso3, pays in PAYS.items():
        for annee in range(debut, fin + 1):
            valeurs = {
                colonne: mesures.get((iso3, annee))
                for colonne, mesures in par_indicateur.items()
            }
            if all(v is None for v in valeurs.values()):
                continue
            rows.append({
                "pays_iso3": iso3,
                "pays": pays,
                "annee": annee,
                **valeurs,
                "recupere_le": recupere_le,
            })

    return rows


def derniere_valeur(rows, colonne):
    """Dernière valeur connue de `colonne` pour chaque pays.

    Les séries ne s'arrêtent pas toutes la même année : le Bénin n'a plus
    de coût d'envoi publié depuis 2020 quand le Sénégal en a jusqu'en
    2023. On prend donc, pays par pays, l'observation la plus récente.
    """
    dernieres = {}
    for r in sorted(rows, key=lambda r: r["annee"]):
        if r[colonne] is not None:
            dernieres[r["pays"]] = (r[colonne], r["annee"])
    return dernieres


def calibration(rows):
    """Dérive du jeu brut les paramètres de calage du générateur.

    Renvoie un dictionnaire directement consommable par
    `generate_transfers.appliquer_calibration` :

    - `poids_cible` : part de chaque pays dans le total des remises
      reçues, normalisée à 1. Remplace les poids inspirés du Findex.
    - `cout_pct` : coût moyen réel d'un envoi vers le pays, en fraction
      (0.0464 pour les 4,64 % du Nigeria). Remplace le tirage uniforme.
    - `annees` : année de l'observation retenue, pays par pays, pour être
      citée dans le rapport.
    """
    volumes = derniere_valeur(rows, "remises_recues_usd")
    couts = derniere_valeur(rows, "cout_envoi_vers_pct")

    total = sum(v for v, _ in volumes.values())
    if not total:
        raise ValueError("aucun volume de remises exploitable")

    return {
        "poids_cible": {pays: v / total for pays, (v, _) in volumes.items()},
        "cout_pct": {pays: v / 100 for pays, (v, _) in couts.items()},
        "annees": {
            "volumes": {pays: a for pays, (_, a) in volumes.items()},
            "couts": {pays: a for pays, (_, a) in couts.items()},
        },
    }


def load_to_bigquery(rows, write_disposition="WRITE_TRUNCATE"):
    """Charge les lignes dans `raw.wb_remittances` via un batch load job.

    Contrairement aux taux, la troncature est le mode par défaut : la
    Banque mondiale révise ses séries passées, et le jeu complet tient en
    une centaine de lignes. Réécrire évite d'avoir à dédupliquer.
    """
    from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
    from google.cloud import bigquery

    from bq_schemas import SCHEMA_WB_REMITTANCES

    if not rows:
        raise ValueError("aucune remise à charger : réponse de l'API vide")

    hook = BigQueryHook(gcp_conn_id="google_cloud_default", use_legacy_sql=False)
    client = hook.get_client()
    table_id = f"{hook.project_id}.raw.wb_remittances"

    job_config = bigquery.LoadJobConfig(
        write_disposition=write_disposition,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=SCHEMA_WB_REMITTANCES,
    )
    load_job = client.load_table_from_json(rows, table_id, job_config=job_config)
    load_job.result()  # attend la fin du job, lève une exception si échec

    return len(rows)
