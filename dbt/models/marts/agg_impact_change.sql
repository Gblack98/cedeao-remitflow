-- Impact du risque de change sur le montant reçu (question 2).
--
-- Tout est ramené à une base commune de 100 000 XOF nets envoyés, sans
-- quoi les écarts refléteraient la dispersion des montants simulés
-- plutôt que celle des taux. L'écart entre le pire et le meilleur jour
-- est le chiffre central du projet.

with base as (
    select
        type_corridor,
        devise_cible,
        nom_devise,
        parite_fixe_eur,
        safe_divide(montant_recu_devise_cible, montant_net_xof) * 100000 as recu_pour_100k
    from {{ ref('obt_transferts') }}
    where statut = 'SUCCESS'
      and taux_marche_eur is not null
      and montant_net_xof > 0
)

select
    type_corridor,
    devise_cible,
    nom_devise,
    parite_fixe_eur,
    count(*) as transferts,
    round(min(recu_pour_100k), 0) as recu_pire_jour,
    round(avg(recu_pour_100k), 0) as recu_moyen,
    round(max(recu_pour_100k), 0) as recu_meilleur_jour,
    round(safe_divide(max(recu_pour_100k) - min(recu_pour_100k), min(recu_pour_100k)) * 100, 1)
        as ecart_max_pct
from base
group by 1, 2, 3, 4
