-- Indicateurs de tête, en une seule ligne.
--
-- Le grain unique est délibéré : une carte de score dans Looker Studio
-- réagrège toujours la colonne qu'on lui donne. Sur une ligne unique,
-- somme et moyenne coïncident, donc le chiffre affiché est juste quel
-- que soit le réglage.

with base as (
    select * from {{ ref('obt_transferts') }}
),

succes as (
    select * from base where statut = 'SUCCESS'
)

select
    (select count(*) from base) as transferts_total,
    (select count(*) from succes) as transferts_reussis,
    round((select count(*) from succes) / (select count(*) from base) * 100, 1) as taux_succes_pct,
    (select sum(montant_source_xof) from succes) as volume_total_xof,
    (select sum(frais_transaction_xof) from succes) as frais_total_xof,
    round((select avg(taux_frais_pct) from succes), 2) as frais_moyen_pct,
    (select count(distinct concat(pays_source, '>', pays_cible)) from succes) as nb_corridors,
    round(
        (select sum(montant_source_xof) from succes
         where type_corridor = 'Avec risque de change')
        / (select sum(montant_source_xof) from succes) * 100, 1
    ) as part_volume_a_risque_pct
