
with source as (
    select * from {{ source('duckdb_local', 'fct_budget_monthly') }}
)
select
    scenario_id,
    month_end::date as month_end,
    fiscal_year,
    budget_mrr,
    budget_customers,
    budget_arr,
    ev_multiple
from source
