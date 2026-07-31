-- Série temporelle des taux de change. Une ligne = une date et une
-- devise. Alimente la courbe de volatilité (question 2).
--
-- L'indice base 100 ramène les trois devises à une échelle commune : le
-- Naira autour de 1 500 et le Cedi autour de 13 sont illisibles sur un
-- même axe, alors que leurs variations relatives se comparent
-- directement une fois indexées sur leur première cotation.

with cotations as (
    select
        date_taux as date_id,
        devise_cible,
        taux
    from {{ ref('stg_taux_change') }}
    where devise_cible in ('NGN', 'GHS', 'XOF')
),

reference as (
    -- Première cotation observée pour chaque devise.
    select
        devise_cible,
        array_agg(taux order by date_id limit 1)[offset(0)] as taux_initial
    from cotations
    group by devise_cible
)

select
    c.date_id,
    c.devise_cible,
    d.nom as nom_devise,
    d.parite_fixe_eur,
    c.taux,
    round(c.taux / r.taux_initial * 100, 2) as indice_base_100
from cotations c
join reference r on c.devise_cible = r.devise_cible
left join {{ ref('dim_devises') }} d on c.devise_cible = d.code_devise
