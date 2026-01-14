
import duckdb
import pandas as pd
import json
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

DB_FILE = "financial_model.duckdb"
CONTRACT_FILE = "business_contract.json"

def run_transformations():
    print("Connecting to DuckDB...")
    con = duckdb.connect(DB_FILE)
    
    with open(CONTRACT_FILE, 'r') as f:
        contract = json.load(f)
        
    print("Building dim_calendar...")
    # Generate dates from 2024-01-01 to 2028-12-31
    dates = []
    start = date(2024, 1, 1)
    end = date(2028, 12, 31)
    curr = start
    while curr <= end:
        dates.append({
            'date_key': curr, 
            'year': curr.year, 
            'month': curr.month, 
            'month_end': (curr + relativedelta(months=1, day=1) - relativedelta(days=1))
        })
        curr += relativedelta(days=1)
        
    df_dates = pd.DataFrame(dates)
    con.execute("CREATE OR REPLACE TABLE dim_calendar AS SELECT * FROM df_dates")
    
    print("Building fct_budget_monthly...")
    # Expand yearly contract to monthly budget
    budget_rows = []
    op = contract['operating_plan']
    for year_str, metrics in op.items():
        year = int(year_str)
        # simplistic: spread yearly targets / 12 for budget tracking if needed
        # Or just carry the yearly target labels.
        # User wants "fct_budget_monthly table is populated directly from the business_contract.json yearly values"
        # Presumably repeated for each month or divided?
        # Revenue Target is Annual. Monthly budget = Annual / 12?
        # Customers End is Year End. Monthly budget implies interpolation or just repeating the year-end goal?
        # Usually linear interpolation for customers.
        # I'll do: Revenue/12. Customers linear interp from previous year end.
        
        # We need previous year end for interp.
        prev_year_end = 0
        if str(year-1) in op:
            prev_year_end = op[str(year-1)]['customers_end']
        elif year == 2024:
            prev_year_end = 0 # Start
            
        target_end = metrics['customers_end']
        monthly_growth = (target_end - prev_year_end) / 12
        
        for m in range(1, 13):
            month_date = date(year, m, 1) + relativedelta(months=1, day=1) - relativedelta(days=1)
            
            budget_rows.append({
                'scenario_id': 1, # BUD
                'month_end': month_date,
                'fiscal_year': year,
                'budget_mrr': (metrics['revenue_target'] / 12), # Already calculated in EUR in extract_contract
                'budget_customers': prev_year_end + (monthly_growth * m),
                'budget_arr': metrics['revenue_target'], # Already in EUR
                'ev_multiple': metrics['ev_multiple']
            })
            
    df_budget = pd.DataFrame(budget_rows)
    con.execute("CREATE OR REPLACE TABLE fct_budget_monthly AS SELECT * FROM df_budget")

    print("Building fct_subscription_snapshot_monthly...")
    # Cross join calendar months with subscriptions to determine status
    # We only care about Month Ends.
    # Logic: For each month_end in 2024-2028:
    #   Find subs where start_date <= month_end AND (end_date IS NULL OR end_date > month_end)
    #   Sum MRR
    
    # Efficient SQL approach
    sql = """
    WITH months AS (
        SELECT DISTINCT month_end 
        FROM dim_calendar 
        WHERE month_end = date_trunc('month', month_end) + interval '1 month' - interval '1 day'
    ),
    snapshots AS (
        SELECT 
            m.month_end,
            s.subscription_id,
            s.customer_id,
            s.mrr,
            s.start_date,
            s.end_date
        FROM months m
        CROSS JOIN raw_subscriptions s
        WHERE TRY_CAST(s.start_date AS DATE) <= m.month_end
          AND (s.end_date IS NULL OR TRY_CAST(s.end_date AS DATE) > m.month_end)
    )
    SELECT 
        2 as scenario_id, -- ACT
        month_end,
        COUNT(DISTINCT customer_id) as active_customers,
        SUM(mrr) as total_mrr,
        SUM(mrr) * 12 as total_arr
    FROM snapshots
    GROUP BY month_end
    ORDER BY month_end
    """
    con.execute(f"CREATE OR REPLACE TABLE fct_subscription_snapshot_monthly AS {sql}")
    
    print("Building fct_valuation_monthly...")
    # Join ACT (snapshot) and BUD (budget) to calculate valuation
    # We want Valuation for ACT? "Apply ev_multiple from contract to the ARR"
    # The ev_multiple is in fct_budget_monthly (derived from contract).
    
    sql_val = """
    SELECT 
        s.scenario_id,
        s.month_end,
        s.total_arr,
        b.ev_multiple,
        s.total_arr * b.ev_multiple as valuation_ev
    FROM fct_subscription_snapshot_monthly s
    LEFT JOIN fct_budget_monthly b ON s.month_end = b.month_end
    UNION ALL
    SELECT
        b.scenario_id,
        b.month_end,
        b.budget_arr as total_arr,
        b.ev_multiple,
        b.budget_arr * b.ev_multiple as valuation_ev
    FROM fct_budget_monthly b
    """
    con.execute(f"CREATE OR REPLACE TABLE fct_valuation_monthly AS {sql_val}")
    
    print("DWH Build Complete.")
    con.close()

if __name__ == "__main__":
    run_transformations()
