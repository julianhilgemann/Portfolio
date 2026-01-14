
  
    
    

    create  table
      "financial_model"."main"."int_subscription_months__dbt_tmp"
  
    as (
      with calendar as (
    select distinct month_end from "financial_model"."main"."dim_calendar"
    where month_end = date_trunc('month', month_end) + interval '1 month' - interval '1 day'
),
subs as (
    select * from "financial_model"."main"."stg_subscriptions"
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
    );
  
  