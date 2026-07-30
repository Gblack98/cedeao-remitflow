-- Date spine couvrant l'année civile 2026.
select
    d as date_id,
    extract(dayofweek from d) as jour_semaine,
    extract(month from d) as mois,
    extract(quarter from d) as trimestre,
    extract(year from d) as annee
from unnest(generate_date_array('2026-01-01', '2026-12-31')) as d
