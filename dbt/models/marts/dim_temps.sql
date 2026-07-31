-- Date spine couvrant la période reprise par backfill_forex_history
-- (à partir de 2024) jusqu'à fin 2027, avec une marge au-delà de l'année
-- en cours pour que la jointure sur la table de faits reste complète.
select
    d as date_id,
    extract(dayofweek from d) as jour_semaine,
    extract(month from d) as mois,
    extract(quarter from d) as trimestre,
    extract(year from d) as annee
from unnest(generate_date_array('2024-01-01', '2027-12-31')) as d
