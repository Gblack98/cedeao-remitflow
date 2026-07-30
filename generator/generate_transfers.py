"""
Génère des transferts d'argent simulés entre pays de la CEDEAO.

Usage :
    python generate_transfers.py --n 5000 --output data/transferts_raw.csv

Le script ne se connecte à aucune API : il simule des transferts entre
corridors réalistes (UEMOA -> UEMOA, UEMOA -> Nigeria, UEMOA -> Ghana) avec
une distribution de volume approximative par pays, inspirée des statistiques
d'inclusion financière du Global Findex (le Sénégal et la Côte d'Ivoire
concentrent une part importante des flux mobile money de la zone UEMOA).
"""

import argparse
import csv
import random
import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker

fake = Faker()

# Poids approximatifs par pays d'émission (tous en UEMOA, donc en XOF)
PAYS_SOURCE_UEMOA = {
    "Senegal": 0.28,
    "Cote d'Ivoire": 0.32,
    "Mali": 0.14,
    "Burkina Faso": 0.12,
    "Benin": 0.09,
    "Togo": 0.05,
}

# Poids par pays de destination : la majorité reste intra-UEMOA
# (pas de risque de change), une minorité part vers le Nigeria ou le Ghana
# (devise flottante, c'est le cœur de l'analyse du projet).
PAYS_CIBLE = {
    "Senegal": 0.28, "Cote d'Ivoire": 0.20, "Mali": 0.10, "Burkina Faso": 0.08,
    "Benin": 0.05, "Togo": 0.04,
    "Nigeria": 0.17,
    "Ghana": 0.08,
}

DEVISE_PAR_PAYS = {
    "Senegal": "XOF", "Cote d'Ivoire": "XOF", "Mali": "XOF",
    "Burkina Faso": "XOF", "Benin": "XOF", "Togo": "XOF",
    "Nigeria": "NGN", "Ghana": "GHS",
}

CANAUX = {"mobile_money": 0.55, "virement_bancaire": 0.20, "cash_pickup": 0.20, "carte": 0.05}
STATUTS = {"SUCCESS": 0.90, "FAILED": 0.07, "PENDING": 0.03}


def _pick(weighted: dict) -> str:
    return random.choices(list(weighted.keys()), weights=list(weighted.values()))[0]


def generate_one(date_du_jour: datetime) -> dict:
    pays_source = _pick(PAYS_SOURCE_UEMOA)
    pays_cible = _pick(PAYS_CIBLE)
    # distribution log-normale : beaucoup de petits transferts, quelques gros
    montant_source = round(random.lognormvariate(10.5, 0.8), 0)
    canal = _pick(CANAUX)
    statut = _pick(STATUTS)

    return {
        "transfert_id": str(uuid.uuid4()),
        "date_transfert": date_du_jour.strftime("%Y-%m-%d"),
        "heure_transfert": fake.time(),
        "pays_source": pays_source,
        "pays_cible": pays_cible,
        "devise_source": "XOF",
        "devise_cible": DEVISE_PAR_PAYS[pays_cible],
        "canal": canal,
        "montant_source_xof": montant_source,
        "frais_transaction_xof": round(montant_source * random.uniform(0.01, 0.045), 0),
        "statut": statut,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=2000, help="nombre de transferts à générer")
    parser.add_argument("--jours", type=int, default=30, help="étale les transferts sur N jours")
    parser.add_argument("--output", default="data/transferts_raw.csv")
    args = parser.parse_args()

    rows = []
    today = datetime.now(timezone.utc)
    for _ in range(args.n):
        jour = today - timedelta(days=random.randint(0, args.jours))
        rows.append(generate_one(jour))

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} transferts générés -> {args.output}")


if __name__ == "__main__":
    main()
