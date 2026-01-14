
with source as (
    select * from {{ source('duckdb_local', 'raw_customers') }}
)
select
    customer_id,
    acquisition_date::date as acquisition_date,
    segment
from source
