-- Table dénormalisée destinée au dashboard.
--
-- Le schéma en étoile reste la modélisation de référence ; cette table
-- l'aplatit en une seule surface pour Looker Studio, qui recompose mal
-- les jointures et impose de les redéfinir à chaque graphique.
--
-- Grain inchangé : une ligne = un transfert.

with f as (
    select * from {{ ref('fct_transferts_cedeao') }}
),

devises as (
    select * from {{ ref('dim_devises') }}
),

corridors as (
    select * from {{ ref('dim_corridor') }}
),

canaux as (
    select * from {{ ref('dim_canaux') }}
),

temps as (
    select * from {{ ref('dim_temps') }}
)

select
    f.transfert_id,

    -- axes temporels
    f.date_id,
    t.annee,
    t.trimestre,
    t.mois,
    t.jour_semaine,

    -- axes géographiques
    f.pays_source,
    f.pays_cible,
    c.zone as zone_cible,

    -- axes devise
    f.devise_cible,
    d.nom as nom_devise,
    d.parite_fixe_eur,
    case
        when d.parite_fixe_eur then 'Sans risque de change'
        else 'Avec risque de change'
    end as type_corridor,

    -- axe canal
    f.canal,
    ca.libelle as libelle_canal,

    f.statut,

    -- mesures en devise d'envoi
    f.montant_source_xof,
    f.frais_transaction_xof,
    f.marge_estimee_xof,
    f.montant_source_xof - f.frais_transaction_xof as montant_net_xof,
    safe_divide(f.frais_transaction_xof, f.montant_source_xof) * 100 as taux_frais_pct,

    -- mesures en devise de réception
    f.taux_marche_eur,
    -- Le XOF étant arrimé à l'euro, on convertit XOF -> EUR -> devise
    -- cible. Le montant reçu dépend donc de la date d'envoi dès que la
    -- devise cible flotte : c'est la mesure au cœur de l'analyse.
    safe_divide(f.montant_source_xof - f.frais_transaction_xof, {{ var('xof_per_eur') }})
        * f.taux_marche_eur as montant_recu_devise_cible

from f
left join devises  d  on f.devise_cible = d.code_devise
left join corridors c on f.pays_cible   = c.pays
left join canaux   ca on f.canal        = ca.canal
left join temps    t  on f.date_id      = t.date_id
