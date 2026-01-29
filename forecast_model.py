
import duckdb
import pandas as pd
from prophet import Prophet
from datetime import datetime, date
import logging

# Suppress Prophet logs
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

DB_FILE = "financial_model.duckdb"
CUTOFF_DATE = "2026-12-31"

def run_forecast():
    con = duckdb.connect(DB_FILE)
    
    # 1. Load ACT data (up to cutoff)
    print(f"Loading ACT data up to {CUTOFF_DATE}...")
    df = con.query(f"SELECT ds, y FROM mart_forecast_input WHERE ds <= '{CUTOFF_DATE}'").to_df()
    
    
    # 2. Forward Cross-Validation (Demonstration)
    print("Running Forward Cross-Validation...")
    
    train = df[df['ds'] < '2026-01-01']
    test = df[df['ds'] >= '2026-01-01']
    
    if len(train) >= 24: # Minimal check
        m_cv = Prophet(seasonality_mode='multiplicative', yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        m_cv.fit(train)
        future_cv = m_cv.make_future_dataframe(periods=12, freq='M')
        
        forecast_cv = m_cv.predict(future_cv)
        
        # Calculate Error
        merged = pd.merge(test, forecast_cv[['ds', 'yhat']], on='ds')
        # Floor at 0
        merged['yhat'] = merged['yhat'].clip(lower=0)
        
        mape = ((merged['y'] - merged['yhat']).abs() / merged['y']).mean()
        print(f"Cross-Validation MAPE (2026 Test): {mape:.2%}")

    # 3. Train Full Model
    # Train on the high-growth regime (post-2025) to accurately capture the new trajectory.
    # Training across the changepoint with limited history may underfit the new trend.
    
    print("Training Forecast Model on 2026 High-Growth Regime...")
    training_data = df[df['ds'] >= '2026-01-01'].copy()
    
    # Use simple linear trend (no seasonality to avoid overfitting on short history)
    m = Prophet(seasonality_mode='additive', yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False)
    m.add_country_holidays(country_name='US') 
    m.fit(training_data)
    
    # 4. Forecast Future (2027-2028)
    future = m.make_future_dataframe(periods=24, freq='M')
    forecast = m.predict(future)
    
    # Filter for future only
    fct = forecast[forecast['ds'] > CUTOFF_DATE][['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
    fct['yhat'] = fct['yhat'].clip(lower=0)

    fct['scenario_id'] = 3 # FCT
    fct['scenario'] = 'FCT'
    
    print(f"Generated {len(fct)} forecast months.")
    print(fct[['ds', 'yhat']].head())
    
    # Write to DuckDB
    # Match schema of fct tables (Scenario, Customers, MRR, ARR)
    # Use placeholder for Customers as we only forecast MRR ('y')
    
    fct_rows = []
    for _, row in fct.iterrows():
        fct_rows.append({
            'month_end': row['ds'],
            'scenario': 'FCT',
            'scenario_id': 3,
            'customers': 0, # Placeholder
            'mrr': row['yhat'],
            'arr': row['yhat'] * 12
        })
        
    df_fct = pd.DataFrame(fct_rows)
    con.execute("CREATE OR REPLACE TABLE raw_forecast AS SELECT * FROM df_fct")
    print("Forecast written to raw_forecast.")
    
    con.close()

if __name__ == "__main__":
    run_forecast()
