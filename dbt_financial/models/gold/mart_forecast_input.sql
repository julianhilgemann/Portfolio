
select
    month_end as ds,
    mrr as y
from {{ ref('mart_finance_monthly') }}
where scenario = 'ACT'
order by ds
