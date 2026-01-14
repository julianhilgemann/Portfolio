
  
  create view "financial_model"."main"."stg_customers__dbt_tmp" as (
    with source as (
    select * from "financial_model"."main"."raw_customers"
)
select
    customer_id,
    acquisition_date::date as acquisition_date,
    segment
from source
  );
