-- Nettoyage de la source brute des taux de change.
-- Une ligne = un taux, pour une devise cible et une date données (base EUR).

with source as (
    select * from {{ source('raw', 'taux_change') }}
)

select
    date_taux,
    upper(devise_base) as devise_base,
    upper(devise_cible) as devise_cible,
    cast(taux as numeric) as taux,
    recupere_le
from source
where taux is not null
