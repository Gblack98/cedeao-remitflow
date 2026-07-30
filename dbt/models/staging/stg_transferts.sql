with source as (
    select * from {{ source('raw', 'transferts') }}
)

select
    transfert_id,
    date_transfert,
    heure_transfert,
    pays_source,
    pays_cible,
    upper(devise_source) as devise_source,
    upper(devise_cible) as devise_cible,
    canal,
    cast(montant_source_xof as numeric) as montant_source_xof,
    cast(frais_transaction_xof as numeric) as frais_transaction_xof,
    statut
from source
where transfert_id is not null
