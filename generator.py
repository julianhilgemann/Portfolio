
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

    # Initialize AR(1) noise
    sigma = 0.1 # Default from prompt
    rho = 0.6   # Default from prompt
    # Check if overrides in exp_noise for 'new_customers'
    for noise_conf in contract.get('exp_noise', []):
        if noise_conf.get('metric') == 'new_customers':
            sigma = noise_conf.get('sigma', sigma)
            rho = noise_conf.get('rho', rho)
    
    eps = 0.0 # Initial noise state
    
    # Seasonality map
    seas_map = {item['month']: item['seasonality_weight'] for item in contract.get('export_seas', [])}
    
    # Churn configurations
    churn_segments = contract.get('exp_churn', [])
    # Default churn rate if not found (Annual 15% -> Monthly ~1.3%)
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
        # Make them active from 2023-01-01
        seed_date = datetime(2023, 1, 1)
        # Use 2024 ARPU
        seed_arpu = operating_plan.get('2024', {}).get('arpu', 1000)
        
        for _ in range(int(start_2024_target)):
            customer_id_counter += 1
            cid = customer_id_counter
            
            mrr = seed_arpu # Flat for seed or lognormal? Lognormal better.
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
        if regime > prev_regime:
            print(f"Regime Change {prev_regime} -> {regime}. Repricing existing customers...")
            # Reprice active customers to current year's ARPU
            # Calculate new MU/SIGMA
            target_arpu = plan.get('arpu', 1000)
            arpu_sigma = 0.05 # simplistic
            mu = np.log(target_arpu) - (arpu_sigma**2)/2
            
            for cust in current_customers:
                # Update MRR
                new_mrr = np.random.lognormal(mu, arpu_sigma)
                cust['mrr'] = new_mrr
                # Update subscription record? 
                # Ideally we end old sub and start new, but for simplicity update the sub record if possible?
                # or just update the mrr in the subscription list object?
                # The subscription list is just a log.
                # We need to find the matching sub object and update mrr?
                # This affects snapshots.
                # If we update the object in the list, transformations will pick it up?
                # transformations joins cross join.
                # Wait, snapshots use `s.mrr`. If `s` is one row per sub, and mrr changes over time, we need SCD Type 2.
                # But our schema is simple: `raw_subscriptions` one row.
                # If I update `mrr` in the dict in `subscriptions` list, it applies retroactively??
                # Yes, because `subscriptions` is a list of dicts.
                # BUT this is wrong. It would change historical MRR.
                # To do it right: End old sub, Start new sub?
                # Or just Hack: `raw_subscriptions` has `mrr`. If I change it, I change history.
                # FIX: `raw_subscriptions` should handle MRR changes?
                # Schema: `subscription_id`, `mrr`.
                # If I can't support MRR changes, I can't fix Revenue without breaking History.
                # UNLESS: I accept history change (since this is a simulation for a future plan).
                # But ACT 2024 should stay valid.
                # If I change MRR in 2026, 2024 MRR changes? Yes.
                
                # Validation relies on 2024, 2025, 2026 snapshots.
                # If I change MRR in memory for the *same* dict object, it changes globally.
                pass
            
            # Since I cannot easily do SCD2 in this simple script without rewriting usage,
            # I will Create NEW subscriptions for the repriced users and End the old ones.
            
            for cust in current_customers:
                cid = cust['customer_id']
                # Find old sub to end
                for sub in subscriptions:
                    if sub['customer_id'] == cid and sub['end_date'] is None:
                        sub['end_date'] = datetime(year, 1, 1).strftime('%Y-%m-%d')
                        break
                
                # Create new sub
                new_mrr = np.random.lognormal(mu, arpu_sigma)
                cust['mrr'] = new_mrr
                subscriptions.append({
                    'subscription_id': f"sub_{cid}_{year}",
                    'customer_id': cid,
                    'start_date': datetime(year, 1, 1).strftime('%Y-%m-%d'),
                    'end_date': None,
                    'mrr': new_mrr,
                    'currency': 'EUR'
                })
                
        prev_regime = regime
        
        # We need to hit target_customers_end by end of year.
        # But we simulate month by month.
        # We calculate the "Yearly Gross Adds Goal" at the start of the year?
        # Or re-evaluate monthly to ensure we hit target?
        # Re-evaluating monthly is a "Control System".
        # Prompt says: "Monthly Envelopes: Use seasonality... distribute yearly targets".
        # This implies a pre-calculation of the monthly target based on the yearly goal.
        
        # Let's estimate:
        # Start of Year Customers
        start_count = len(current_customers)
        net_add_goal = target_customers_end - start_count
        
        # Expected Churn Loss?
        # Rough estimate: Start Count * Annual Churn Rate?
        # + New Adds * (Annual Churn Rate / 2)?
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
            # Target End = target_customers_end
            # Current = len(current_customers)
            # Gap = Target End - Current
            # Remaining months = 13 - month
            # Required Net Adds per month = Gap / Remaining
            # Expected Churn this month = Current * monthly_churn_prob
            # Gross Target = Required Net + Expected Churn
            
            # Note: We still respect seasonality relative to remaining months?
            # Or just flat spread of the gap?
            # To respect seasonality: 
            # Remaining Weight = Sum of weights for month...12
            # Weight Fraction = weight / Remaining Weight
            # Gross Target = Gap * Weight Fraction + Churn
            # BUT Gap includes future churn? No, Gap is just Headcount.
            # We need to add *immediate* expected churn to stay flat, plus growth.
            
            current_count = len(current_customers)
            gap = target_customers_end - current_count
            
            # Sum remaining weights
            remaining_weights = sum([seas_map.get(m, 1.0) for m in range(month, 13)])
            weight = seas_map.get(month, 1.0)
            
            if remaining_weights > 0:
                net_target = gap * (weight / remaining_weights)
            else:
                net_target = 0
            
            # Expected churn replacement
            expected_churn_replacement = current_count * monthly_churn_prob
            
            # Base Target
            monthly_target_base = max(0, net_target + expected_churn_replacement)
            
            # 2. Apply Regime Smoothing AR(1) Noise
            # eps_t = rho * eps_{t-1} + sigma * N(0,1)
            noise_term = np.random.normal(0, 1)
            eps = rho * eps + sigma * noise_term
            
            # Apply multiplier: exp(eps) or (1 + eps)? Lognormal usually means multiplication.
            # "Apply AR(1) noise" -> usually multiplicative for volumes.
            # Using max(0, ...) to avoid negative
            noisy_target = monthly_target_base * np.exp(eps)
            
            # 3. Generate Granular Arrivals (Poisson)
            # Poisson lambda = noisy_target
            # We treat the monthly sum as the realization of a Poisson process?
            # Or we simulate daily? Prompt: "Use Poisson processes for daily arrivals."
            # So lambda_day = noisy_target / days_in_month
            days_in_month = 30 # Approximation
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
                    # Contract ARPU is the mean. Lognormal needs mu and sigma of underlying normal.
                    # Mean of lognormal = exp(mu + sigma^2/2)
                    # We have Mean (plan['arpu']) and Sigma (from exp_noise 'arpu' ~0.05).
                    # approx: if sigma is small, std dev / mean approx sigma.
                    # let's use the sigma from exp_noise.
                    target_arpu = plan.get('arpu', 1000)
                    arpu_sigma = 0.05
                    for n in contract.get('exp_noise', []):
                        if n['metric'] == 'arpu':
                            arpu_sigma = n['sigma']
                            
                    # Solving for mu:
                    # mean = exp(mu + s^2/2) -> log(mean) = mu + s^2/2 -> mu = log(mean) - s^2/2
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

            # 4. Generate Churn (Hazard Based)
            # Iterate through current active customers and determine if they churn today/this month.
            # Simplification: evaluate churn once per month for all active users?
            # Or daily? Hazard usually implies continuous time.
            # "Hazard-Based Churn with tenure decay"
            # Probability(Churn in dt) = h(t) * dt
            # h(t) = base_multiplier * t^(-beta) ? Or something similar.
            # Let's use: Prob = Base * (1 / (1 + beta * tenure_months))?
            # Or contract says `tenure_decay_beta`.
            # Let's assume P(churn this month) = MonthlyBase * (TenureMonths ^ -beta).
            # If tenure < 1 month, use tenure=1.
            
            indices_to_remove = []
            for idx, cust in enumerate(current_customers):
                tenure_days = (current_date - cust['start_date']).days
                tenure_months = max(1, tenure_days / 30)
                
                # Find segment params
                seg_params = next((s for s in churn_segments if s['segment'] == cust['segment']), {'base_multiplier':1.0, 'tenure_decay_beta': 0.1})
                
                # Base prob scaled by global assumed monthly churn (1.3%) * multiplier
                # Wait, base_multiplier is around 1.0. 
                # So h(t) = monthly_churn_prob * base_multiplier * (tenure_months ^ -beta)
                
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
