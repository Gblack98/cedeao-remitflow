-- Coût de commission par canal et par type de corridor (question 3).
-- Une ligne = un couple canal / type de corridor.

select
    canal,
    libelle_canal,
    type_corridor,
    zone_cible,

    count(*) as transferts,
    sum(montant_source_xof) as volume_xof,
    round(avg(taux_frais_pct), 2) as frais_moyen_pct,
    round(avg(frais_transaction_xof), 0) as frais_moyen_xof,
    round(avg(marge_estimee_xof), 0) as marge_moyenne_xof

from {{ ref('obt_transferts') }}
where statut = 'SUCCESS'
group by 1, 2, 3, 4
