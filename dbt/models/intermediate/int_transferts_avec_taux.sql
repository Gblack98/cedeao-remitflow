-- Rattache à chaque transfert le taux de change EUR -> devise cible en
-- vigueur le jour du transfert, pour calculer ensuite l'écart entre les
-- frais facturés et le taux de marché.
--
-- Attention : join "as of date" simple. Si le DAG de taux de change n'a
-- pas tourné un jour donné (weekend, panne), taux_marche_eur sera NULL
-- pour les transferts de ce jour — à surveiller via le test de fraîcheur
-- sur la source (_staging.yml).

with transferts as (
    select * from {{ ref('stg_transferts') }}
),

taux as (
    select * from {{ ref('stg_taux_change') }}
)

select
    t.*,
    tx.taux as taux_marche_eur
from transferts t
left join taux tx
    on t.devise_cible = tx.devise_cible
    and t.date_transfert = tx.date_taux
