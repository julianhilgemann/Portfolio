
import json
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

CONTRACT_FILE = "business_contract.json"
DB_FILE = "financial_model.duckdb"

def run_generator():
    print(f"Loading contract from {CONTRACT_FILE}...")
    with open(CONTRACT_FILE, 'r') as f:
        contract = json.load(f)

    # Initialize AR(1) noise parameters
    sigma = 0.1
    rho = 0.6
    for noise_conf in contract.get('exp_noise', []):
        if noise_conf.get('metric') == 'new_customers':
            sigma = noise_conf.get('sigma', sigma)
            rho = noise_conf.get('rho', rho)
    
    eps = 0.0 # Initial noise state
    
    # Seasonality map
    seas_map = {item['month']: item['seasonality_weight'] for item in contract.get('export_seas', [])}
    
    # Calculate monthly churn probability from annual rate
    churn_segments = contract.get('exp_churn', [])
    annual_churn_rate = 0.15
    monthly_churn_prob = 1 - (1 - annual_churn_rate)**(1/12)
    
    # Data containers
    customers = []
    subscriptions = []
    
    customer_id_counter = 1000
    
    # Simulation State
    current_customers = [] # List of active customer dicts
    
    # Fiscal Years
    operating_plan = contract.get('operating_plan', {})
    years = sorted([int(k) for k in operating_plan.keys()])
    
    # Determine start date
    start_date = datetime.fromisoformat(contract['meta'][3]['Example']) if 'meta' in contract else datetime(2024, 1, 1)

    # Connect DB
    con = duckdb.connect(DB_FILE)
    
    # Pre-seed customers if 2024 expects a base
    # Based on assumption that Start 2024 ~ End 2024 (30 customers)
    start_2024_target = operating_plan.get('2024', {}).get('customers_end', 0)
    if start_2024_target > 0:
        print(f"Seeding {int(start_2024_target)} initial customers...")
        seed_date = datetime(2023, 1, 1)
        seed_arpu = operating_plan.get('2024', {}).get('arpu', 1000)
        
        for _ in range(int(start_2024_target)):
            customer_id_counter += 1
            cid = customer_id_counter
            
            # Generate MRR using lognormal distribution
            arpu_sigma = 0.05
            mu = np.log(seed_arpu) - (arpu_sigma**2)/2
            mrr = np.random.lognormal(mu, arpu_sigma)
            
            cust = {
                'customer_id': cid,
                'start_date': seed_date,
                'segment': 'SMB', # Default
                'status': 'active',
                'mrr': mrr,
                'regime_at_signup': 1.0
            }
            current_customers.append(cust)
            customers.append({
                'customer_id': cid,
                'acquisition_date': seed_date.strftime('%Y-%m-%d'),
                'segment': 'SMB'
            })
            subscriptions.append({
                'subscription_id': f"sub_{cid}",
                'customer_id': cid,
                'start_date': seed_date.strftime('%Y-%m-%d'),
                'end_date': None,
                'mrr': mrr,
                'currency': 'EUR'
            })
            
    print("Starting simulation...")
    
    prev_regime = 1.0
    
    for year in years:
        year_str = str(year)
        plan = operating_plan[year_str]
        
        target_customers_end = plan.get('customers_end', 0)
        regime = plan.get('regime', 1.0)
        
        # Repricing Event if Regime increases
        # Handle Regime Change: Reprice existing customers
        if regime > prev_regime:
            print(f"Regime Change {prev_regime} -> {regime}. Repricing existing customers...")
            
            target_arpu = plan.get('arpu', 1000)
            arpu_sigma = 0.05
            mu = np.log(target_arpu) - (arpu_sigma**2)/2
            
            # Create new subscriptions for repriced users to preserve history
            for cust in current_customers:
                # End old subscription
                for sub in subscriptions:
                    if sub['customer_id'] == cust['customer_id'] and sub['end_date'] is None:
                        sub['end_date'] = datetime(year, 1, 1).strftime('%Y-%m-%d')
                        break
                
                # Start new subscription with updated MRR
                new_mrr = np.random.lognormal(mu, arpu_sigma)
                cust['mrr'] = new_mrr
                subscriptions.append({
                    'subscription_id': f"sub_{cust['customer_id']}_{year}",
                    'customer_id': cust['customer_id'],
                    'start_date': datetime(year, 1, 1).strftime('%Y-%m-%d'),
                    'end_date': None,
                    'mrr': new_mrr,
                    'currency': 'EUR'
                })
            

                
        prev_regime = regime
        
        # Calculate yearly goals
        start_count = len(current_customers)
        net_add_goal = target_customers_end - start_count
        expected_churn = (start_count * annual_churn_rate)
        gross_add_goal = max(0, net_add_goal + expected_churn)
        
        # Distribute Gross Add Goal by Seasonality
        # Sum of seasonality weights for 12 months?
        total_seas = sum(seas_map.values())
        
        print(f"Year {year}: Start {start_count}, Target End {target_customers_end}, Gross Goal {gross_add_goal:.2f}")

        # Iterate months
        # Note: simplistic month iteration
        for month in range(1, 13):
            # Update date
            current_date = datetime(year, month, 1)
            
            # 1. Calculate Monthly Target (Gross Adds) using Control Loop
            current_count = len(current_customers)
            gap = target_customers_end - current_count
            
            # Sum remaining weights for seasonality
            remaining_weights = sum([seas_map.get(m, 1.0) for m in range(month, 13)])
            weight = seas_map.get(month, 1.0)
            
            if remaining_weights > 0:
                net_target = gap * (weight / remaining_weights)
            else:
                net_target = 0
            
            # Account for churn replacement
            expected_churn_replacement = current_count * monthly_churn_prob
            monthly_target_base = max(0, net_target + expected_churn_replacement)
            
            # 2. Apply Regime Smoothing AR(1) Noise
            noise_term = np.random.normal(0, 1)
            eps = rho * eps + sigma * noise_term
            noisy_target = monthly_target_base * np.exp(eps)
            
            # 3. Generate Granular Arrivals (Poisson)
            days_in_month = 30
            lambda_day = noisy_target / days_in_month
            
            actual_adds_this_month = 0
            
            for day in range(1, 31): # Daily simulation
                sim_date = current_date + timedelta(days=day-1)
                
                # Daily Arrivals
                n_arrivals = np.random.poisson(lambda_day)
                actual_adds_this_month += n_arrivals
                
                for _ in range(n_arrivals):
                    customer_id_counter += 1
                    cid = customer_id_counter
                    
                    # Attributes
                    segment = random.choices(
                        [s['segment'] for s in churn_segments],
                        k=1
                    )[0] if churn_segments else 'SMB'
                    
                    # Generate ARPU (Lognormal)
                    target_arpu = plan.get('arpu', 1000)
                    arpu_sigma = 0.05
                    for n in contract.get('exp_noise', []):
                        if n['metric'] == 'arpu':
                            arpu_sigma = n['sigma']
                            
                    # Calculate mu from mean/sigma for lognormal
                    mu = np.log(target_arpu) - (arpu_sigma**2)/2
                    
                    mrr = np.random.lognormal(mu, arpu_sigma)
                    
                    cust = {
                        'customer_id': cid,
                        'start_date': sim_date,
                        'segment': segment,
                        'status': 'active',
                        'mrr': mrr,
                        'regime_at_signup': regime
                    }
                    current_customers.append(cust)
                    customers.append({
                        'customer_id': cid,
                        'acquisition_date': sim_date.strftime('%Y-%m-%d'),
                        'segment': segment
                    })
                    subscriptions.append({
                        'subscription_id': f"sub_{cid}",
                        'customer_id': cid,
                        'start_date': sim_date.strftime('%Y-%m-%d'),
                        'end_date': None,
                        'mrr': mrr,
                        'currency': 'EUR'
                    })

            # 4. Hazard-Based Churn
            indices_to_remove = []
            for idx, cust in enumerate(current_customers):
                tenure_days = (current_date - cust['start_date']).days
                tenure_months = max(1, tenure_days / 30)
                
                seg_params = next((s for s in churn_segments if s['segment'] == cust['segment']), {'base_multiplier':1.0, 'tenure_decay_beta': 0.1})
                
                # Probability = MonthlyBase * BaseMult * (Tenure^-Beta)
                prob = monthly_churn_prob * seg_params['base_multiplier'] * (tenure_months ** -seg_params['tenure_decay_beta'])
                
                if random.random() < prob:
                    # CHURN
                    churn_date = current_date + timedelta(days=random.randint(0, 29))
                    cust['status'] = 'churned'
                    indices_to_remove.append(idx)
                    
                    # Update subscription
                    # Naively find the matching sub (assuming 1 sub per cust)
                    for sub in subscriptions:
                        if sub['customer_id'] == cust['customer_id']:
                            sub['end_date'] = churn_date.strftime('%Y-%m-%d')
                            break
            
            # Remove churned from active list (iterate reverse to avoid index shift)
            for idx in sorted(indices_to_remove, reverse=True):
                del current_customers[idx]
                
            # print(f"  M{month}: Added {actual_adds_this_month}, Churned {len(indices_to_remove)}, End {len(current_customers)}")

    # Write to DuckDB
    print("Writing to DuckDB...")
    df_cust = pd.DataFrame(customers)
    df_subs = pd.DataFrame(subscriptions)
    
    con.execute("CREATE OR REPLACE TABLE raw_customers AS SELECT * FROM df_cust")
    con.execute("CREATE OR REPLACE TABLE raw_subscriptions AS SELECT * FROM df_subs")
    
    print("Done.")
    con.close()

if __name__ == "__main__":
    run_generator()
