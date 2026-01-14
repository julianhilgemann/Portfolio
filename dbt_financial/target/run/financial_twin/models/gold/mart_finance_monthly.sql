
  
    
    

    create  table
      "financial_model"."main"."mart_finance_monthly__dbt_tmp"
  
    as (
      with act as (
    select
        month_end,
        'ACT' as scenario,
        2 as scenario_id,
        count(distinct customer_id) as customers,
        sum(mrr) as mrr,
        sum(mrr) * 12 as arr
    from "financial_model"."main"."int_subscription_months"
    group by 1
),
bud as (
    select
        month_end,
        'BUD' as scenario,
        1 as scenario_id,
        budget_customers as customers,
        budget_mrr as mrr,
        budget_arr as arr
    from "financial_model"."main"."stg_budget"
)

select * from act
union all
select * from bud
    );
  
  