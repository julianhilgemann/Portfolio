
  
  create view "financial_model"."main"."stg_subscriptions__dbt_tmp" as (
    with source as (
    select * from "financial_model"."main"."raw_subscriptions"
)
select
    subscription_id,
    customer_id,
    start_date::date as start_date,
    end_date::date as end_date,
    mrr,
    currency
from source
  );
