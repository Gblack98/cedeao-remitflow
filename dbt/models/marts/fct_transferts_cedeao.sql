-- Grain : une ligne = un transfert individuel.
select
    transfert_id,
    date_transfert as date_id,
    pays_source,
    pays_cible,
    devise_source,
    devise_cible,
    canal,
    montant_source_xof,
    frais_transaction_xof,
    taux_marche_eur,
    statut,
    -- Marge simplifiée : écart entre les frais réellement facturés et un
    -- coût de référence théorique à 2%.
    frais_transaction_xof - (montant_source_xof * 0.02) as marge_estimee_xof
from {{ ref('int_transferts_avec_taux') }}
