
  
    
    

    create  table
      "financial_model"."main"."mart_forecast_input__dbt_tmp"
  
    as (
      select
    month_end as ds,
    mrr as y
from "financial_model"."main"."mart_finance_monthly"
where scenario = 'ACT'
order by ds
    );
  
  