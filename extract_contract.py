import pandas as pd
import json
import os

EXCEL_FILE = "/Users/admin/Desktop/Portfolio/B2B SaaS Model.xlsx"
OUTPUT_FILE = "business_contract.json"

def extract_contract():
    print(f"Loading {EXCEL_FILE}...")
    xls = pd.ExcelFile(EXCEL_FILE)
    
    contract = {}
    

    print(f"DEBUG: All sheet names: {xls.sheet_names}")

    # 1. EXPORT_META
    if 'EXPORT_META' in xls.sheet_names:
        df_meta = pd.read_excel(xls, 'EXPORT_META')
        print(f"DEBUG: Head of EXPORT_META:\n{df_meta.head()}")
        contract['meta'] = df_meta.to_dict(orient='records')
    else:
        print("WARNING: EXPORT_META not found")

    
    # 2. Extract Operating Plan from 02_Model (Primary)
    # Using 02_Model as it contains the full multi-year plan (unlike EXPORT_OP).
    if '02_Model' in xls.sheet_names:
        print("Using 02_Model for Operating Plan extraction...")
        df_model = pd.read_excel(xls, '02_Model', header=None)
        
        # Find the header row (starts with Fiscal Year)
        header_row_idx = None
        for i, row in df_model.iterrows():
            if str(row[0]).strip() == 'Fiscal Year':
                header_row_idx = i
                break
        
        if header_row_idx is not None:
            # Extract years
            years = df_model.iloc[header_row_idx, 1:6].tolist() # Columns 1-5 expected
            # Clean years (remove .0)
            years = [int(y) for y in years if pd.notnull(y)]
            
            op_dict = {y: {'fiscal_year': y} for y in years}
            
            # Map metrics by scanning column 0
            metric_map = {
                'Customer Count': 'customers_end',
                'Total Revenue': 'revenue_target',
                'OpEx': 'opex_fixed',
                'S&M': 'marketing_spend',
                'Gross Margin %': 'gross_margin',
                'Multiple': 'ev_multiple',
                'Regime': 'regime'
            }
            
            for i, row in df_model.iterrows():
                label = str(row[0]).strip()
                if label in metric_map:
                    key = metric_map[label]
                    for j, y in enumerate(years):
                        col_idx = j + 1
                        val = row[col_idx]
                        if pd.notnull(val):
                            op_dict[y][key] = val
                            
            # Calculate ARPU (Revenue / Avg Customers / 12) * 1000 (units in kEUR)
            def get_start_count(y, op_dict):
                py = y - 1
                if py in op_dict:
                     return op_dict[py]['customers_end']
                # Assume stable base for 2024 start
                if y == 2024:
                    return op_dict[y]['customers_end']
                return 0
            
            for y in years:
                if 'revenue_target' in op_dict[y] and 'customers_end' in op_dict[y]:
                    rev = op_dict[y]['revenue_target'] * 1000
                    end_cust = op_dict[y]['customers_end']
                    start_cust = get_start_count(y, op_dict)
                    avg_cust = (start_cust + end_cust) / 2
                    
                    if avg_cust > 0:
                        op_dict[y]['arpu'] = rev / avg_cust / 12
                    else:
                         op_dict[y]['arpu'] = 0

            contract['operating_plan'] = op_dict
        else:
            print("WARNING: Could not find 'Fiscal Year' header in 02_Model")

    # Fallback to EXPORT_OP if 02_Model failed or not found
    if 'operating_plan' not in contract and 'EXPORT_OP' in xls.sheet_names:
        # Code from before...
        pass 
        
    # Standardize scaling
    # Convert kEUR to EUR for financial items
    if 'operating_plan' in contract:
        for year, data in contract['operating_plan'].items():
            for k, v in data.items():
                if k in ['revenue_target', 'opex_fixed', 'marketing_spend', 'core_saas_revenue']:
                    # Scale kEUR to EUR
                    # Note: ARPU was calculated already in EUR above.
                    contract['operating_plan'][year][k] = v * 1000
    
    # 3. EXP_NOISE, EXP_CHURN, EXP_MIX, EXP_CHANNEL, EXPORT_SEAS
    simple_sheets = ['EXP_NOISE', 'EXP_CHURN', 'EXP_MIX', 'EXP_CHANNEL', 'EXPORT_SEAS']
    for sheet in simple_sheets:
        if sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet)
            contract[sheet.lower()] = df.to_dict(orient='records')
        else:
            print(f"WARNING: {sheet} not found")

    # 4. Regime Switch from Assumptions
    if 'Assumptions' in xls.sheet_names:
        df_assumptions = pd.read_excel(xls, 'Assumptions', header=None)
        # Search for "Regime Switch" or "Transition Year" in Assumptions sheet
        regime_year = None
        for i, row in df_assumptions.iterrows():
            row_str = row.astype(str).tolist()
            for cell in row_str:
                if 'Regime Switch' in cell or 'Transition Year' in cell:
                    for sub_cell in row_str:
                        try:
                            val = float(sub_cell)
                            if 2020 < val < 2040: 
                                regime_year = int(val)
                                break
                        except:
                            continue
            if regime_year:
                break
        
        if regime_year:
            contract['regime_switch_year'] = regime_year
            print(f"Found Regime Switch Year: {regime_year}")
        else:
            print("WARNING: Could not identify Regime Switch Year in Assumptions")
            contract['regime_switch_year'] = 4 # Default to Year 4 as per prompt hint "Year 4 transition"



    def json_serial(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, (pd.Timestamp, pd.DatetimeIndex)):
            return obj.isoformat()
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return str(obj)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(contract, f, indent=4, default=json_serial)
    
    print(f"Contract saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_contract()
