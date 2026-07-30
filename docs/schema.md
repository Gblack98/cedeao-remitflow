# Schéma en étoile

Grain de la table de faits : **un transfert individuel**.

```mermaid
erDiagram
    FCT_TRANSFERTS_CEDEAO }o--|| DIM_DEVISES : devise_cible
    FCT_TRANSFERTS_CEDEAO }o--|| DIM_CORRIDOR : pays_cible
    FCT_TRANSFERTS_CEDEAO }o--|| DIM_CANAUX : canal
    FCT_TRANSFERTS_CEDEAO }o--|| DIM_TEMPS : date_id

    FCT_TRANSFERTS_CEDEAO {
        string transfert_id PK
        date date_id FK
        string pays_source
        string pays_cible FK
        string devise_cible FK
        string canal FK
        numeric montant_source_xof
        numeric frais_transaction_xof
        numeric taux_marche_eur
        numeric marge_estimee_xof
        string statut
    }
    DIM_DEVISES {
        string code_devise PK
        string nom
        bool parite_fixe_eur
    }
    DIM_CORRIDOR {
        string pays PK
        string zone
    }
    DIM_CANAUX {
        string canal PK
        string libelle
    }
    DIM_TEMPS {
        date date_id PK
        int jour_semaine
        int mois
        int trimestre
    }
```

## Pourquoi ce découpage

- `dim_devises` porte le flag `parite_fixe_eur`, qui sépare les corridors sans risque de change (XOF -> XOF) de ceux avec risque réel (XOF -> NGN, XOF -> GHS). C'est le cœur de la problématique, d'où une colonne explicite plutôt qu'une déduction refaite à chaque requête.
- `dim_corridor` reste simple (pays + zone), ce qui suffit à répondre aux questions métier retenues.
- Pas de dimension `dim_client` : les transferts sont anonymes, aucune donnée utilisateur n'est collectée.
