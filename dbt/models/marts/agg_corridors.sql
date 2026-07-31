-- Volume et valeur par corridor. Une ligne = un couple pays émetteur /
-- pays récepteur. Alimente le classement des corridors (question 1).

select
    pays_source,
    pays_cible,
    zone_cible,
    type_corridor,
    devise_cible,

    count(*) as transferts,
    sum(montant_source_xof) as volume_xof,
    sum(montant_net_xof) as volume_net_xof,
    sum(frais_transaction_xof) as frais_xof,
    round(avg(montant_source_xof), 0) as montant_moyen_xof,
    round(avg(taux_frais_pct), 2) as frais_moyen_pct

from {{ ref('obt_transferts') }}
where statut = 'SUCCESS'
group by 1, 2, 3, 4, 5
