
with calendar as (
    select distinct month_end from {{ source('duckdb_local', 'dim_calendar') }}
    where month_end = date_trunc('month', month_end) + interval '1 month' - interval '1 day'
),
subs as (
    select * from {{ ref('stg_subscriptions') }}
)
select
    c.month_end,
    s.subscription_id,
    s.customer_id,
    s.mrr,
    s.currency
from calendar c
cross join subs s
where s.start_date <= c.month_end
  and (s.end_date is null or s.end_date > c.month_end)
