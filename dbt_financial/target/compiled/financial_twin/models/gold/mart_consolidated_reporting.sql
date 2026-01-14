with act as (
    select
        month_end,
        'ACT' as scenario,
        2 as scenario_id,
        customers,
        mrr,
        arr
    from "financial_model"."main"."mart_finance_monthly"
    where scenario = 'ACT'
),
bud as (
    select
        month_end,
        'BUD' as scenario,
        1 as scenario_id,
        customers,
        mrr,
        arr
    from "financial_model"."main"."mart_finance_monthly"
    where scenario = 'BUD'
),
fct as (
    select
        month_end,
        'FCT' as scenario,
        3 as scenario_id,
        customers,
        mrr,
        arr
    from "financial_model"."main"."raw_forecast"
)

select * from act
union all
select * from bud
union all
select * from fct