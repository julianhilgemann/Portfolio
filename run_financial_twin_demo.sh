#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🚀 Starting Financial Digital Twin Demo...${NC}"

echo -e "${GREEN}[1/5] Extracting Contract from Excel...${NC}"
python3.11 extract_contract.py

echo -e "${GREEN}[2/5] Running Stochastic Generator (ACT)...${NC}"
python3.11 generator.py

echo -e "${GREEN}[3/5] Building Data Warehouse (Bronze/Silver/Gold)...${NC}"
cd dbt_financial
dbt run --profiles-dir .
cd ..

echo -e "${GREEN}[4/5] Generating ML Forecast (FCT)...${NC}"
python3.11 forecast_model.py

echo -e "${GREEN}[5/5] Re-building DWH with Forecasts...${NC}"
cd dbt_financial
dbt run --profiles-dir .
cd ..

echo -e "${CYAN}✅ Pipeline Complete! Launching Dashboard...${NC}"
streamlit run dashboard.py
