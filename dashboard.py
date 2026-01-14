
import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Config
st.set_page_config(page_title="Financial Digital Twin", layout="wide")
DB_FILE = "financial_model.duckdb"

# Load Data
@st.cache_data
def load_data():
    con = duckdb.connect(DB_FILE)
    df = con.query("SELECT * FROM mart_consolidated_reporting ORDER BY month_end").to_df()
    con.close()
    return df

df = load_data()

# Header
st.title("Financial Digital Twin: Executive View")
st.markdown("### Budget vs Actuals vs Forecast")

# Filters
years = df['month_end'].dt.year.unique()
selected_years = st.multiselect("Select Years", years, default=years)

# Filter data
df_filtered = df[df['month_end'].dt.year.isin(selected_years)]

# Main KPIs (Latest Month Available)
# We find the latest month with ACT data
latest_act_date = df[df['scenario'] == 'ACT']['month_end'].max()
if pd.isna(latest_act_date):
    latest_act_date = df['month_end'].max()

# Get metrics for latest month
def get_metrics(date, scenario):
    row = df[(df['month_end'] == date) & (df['scenario'] == scenario)]
    if not row.empty:
        return row.iloc[0]
    return None

curr_act = get_metrics(latest_act_date, 'ACT')
curr_bud = get_metrics(latest_act_date, 'BUD')

# KPI Rows
c1, c2, c3, c4 = st.columns(4)

if curr_act is not None:
    c1.metric("Current ARR", f"€{curr_act['arr']/1e6:.2f}M", 
              delta=f"{(curr_act['arr'] - curr_bud['arr'])/curr_bud['arr']:.1%}" if curr_bud is not None else None)
    
    c2.metric("Customers", f"{int(curr_act['customers'])}",
              delta=f"{int(curr_act['customers'] - curr_bud['customers'])}" if curr_bud is not None else None)
    
    c3.metric("MRR", f"€{curr_act['mrr']/1e3:.1f}k")
else:
    c1.metric("Current ARR", "N/A")

# Forecast Info
fct_end_date = df[df['scenario'] == 'FCT']['month_end'].max()
if pd.notnull(fct_end_date):
    fct_val = get_metrics(fct_end_date, 'FCT')
    c4.metric("Forecasted ARR (End of Plan)", f"€{fct_val['arr']/1e6:.2f}M" if fct_val is not None else "N/A")

st.divider()

# Charts
tab1, tab2 = st.tabs(["ARR Evolution", "Customer Growth"])

with tab1:
    fig_arr = px.line(df_filtered, x='month_end', y='arr', color='scenario', 
                      title="Annual Recurring Revenue (ARR)",
                      color_discrete_map={"ACT": "blue", "BUD": "gray", "FCT": "green"})
    st.plotly_chart(fig_arr, use_container_width=True)

with tab2:
    fig_cust = px.line(df_filtered, x='month_end', y='customers', color='scenario', 
                       title="Active Customers",
                       color_discrete_map={"ACT": "blue", "BUD": "gray", "FCT": "green"})
    st.plotly_chart(fig_cust, use_container_width=True)

# Data Table
with st.expander("Raw Data View"):
    st.dataframe(df_filtered)
