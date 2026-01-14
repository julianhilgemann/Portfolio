
with source as (
    select * from {{ source('duckdb_local', 'raw_subscriptions') }}
)
select
    subscription_id,
    customer_id,
    start_date::date as start_date,
    end_date::date as end_date,
    mrr,
    currency
from source
