# Agentic Financial Twin: Rapid Data Function POC 🚀

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)
![dbt](https://img.shields.io/badge/dbt-FF694B?style=for-the-badge&logo=dbt&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)
![Prophet](https://img.shields.io/badge/Prophet-ML-0057B8?style=for-the-badge&logo=meta&logoColor=white)

> **Building a commercial-grade Financial Data Platform in hours, not weeks, using Agentic Workflow.**

## 📖 About
![High Level Architecture](docs/assets/high_level_architecture.png)

This project is a Proof of Concept (POC) for a **"Rapid Data Function"**—instantiating an entire end-to-end data stack (Stochastic Simulation, Data Warehouse, Algorithmic Forecasting, and BI) purely from a static business definition.

By treating the "Business Contract" (Excel Model) as code, we compile strategy into a living **Financial Digital Twin** that simulates daily operations, scales data engineering via dbt, and performs autonomous forecasting.

## 🤖 The Agentic Workflow
This repository was built using a highly structured **Agent-Assisted** methodology, maximizing the "Context Window" efficiency of LLMs to go from Idea to Execution rapidly.

1.  **Ideation & Alignment**: Brainstorming with **ChatGPT** until the specific "Financial Digital Twin" concept was locked.
2.  **Context Storage**: Structuring the domain knowledge into Markdown modules within an **Obsidian Vault**.
3.  **Retrieval Layer**: Uploading the vault to **NotebookLM** to act as a RAG (Retrieval-Augmented Generation) interface for the project specs.
4.  **Specification**: Using the RAG layer to synthesize a final, technically rigorous "Spec Sheet" (`Downspec.md`).
5.  **Execution**: Feeding the specs into an **Agentic IDE** (e.g., Cursor/Windsurf) to implement the stack, referencing specific context headers.

## 🏗 Architecture
A modern, self-contained data stack running locally:

![System Architecture](docs/assets/architecture_v2.png)

## 📊 Financial Model Foundation
At the heart of the system is the **Business Contract**—a structured extraction of the Excel Operating Plan. This serves as the single source of truth, defining the assumptions (churn, growth, pricing) and the targets that the Stochastic Engine must simulate against.

![Financial Model Foundation](docs/assets/financial_model_foundation.png)

## ⚙️ Generator Dynamics
The simulation engine relies on the following stochastic distributions to model real-world variance:

![Generator Distributions](docs/assets/generator_distributions.png)

## ⚡️ Key Features
-   **Contract-First Engineering**: The entire simulation scales dynamically based on `business_contract.json` extracted from the Excel Operating Plan.
-   **Stochastic Engine**: Simulates Customer Acquisition (Poisson), Retention (Hazard/Survival), and Revenue expansion (Repricing Regimes).
-   **Medallion DWH**: A rigorous `dbt` project structure (Bronze/Silver/Gold) ensuring clean lineage and correct MRR calculations.
-   **Regime-Aware Forecasting**: A `Prophet` model that detects "Growth Regimes" to avoid overfitting on early-stage data.
-   **Three-Pronged BI**: Visualizes the **Plan** (BUD), the **Reality** (ACT), and the **Trend** (FCT) in one unified dashboard.

## 🗄️ Data Warehouse Structure

### Entity Relationship Diagram (ERD)
The core schema centers on the **Subscription** entity, which captures the lifecycle of revenue generation.

```mermaid
erDiagram
    CUSTOMERS ||--o{ SUBSCRIPTIONS : "has"
    CUSTOMERS {
        int customer_id PK
        string segment
        date acquisition_date
    }
    SUBSCRIPTIONS {
        string subscription_id PK
        int customer_id FK
        decimal mrr
        date start_date
        date end_date
    }
    BUDGET_MONTHLY {
        date month_end
        decimal budget_mrr
        int budget_customers
    }
```

### dbt Lineage & Information Flow
Data flows from the Stochastic Engine into the Bronze Layer, transforms into Monthly Recurring Revenue (MRR) ledgers in Silver, and aggregates for Reporting/ML usage in Gold. The Forecast Agent consumes Gold data and writes back predictions to complete the loop.

```mermaid
graph TD
    classDef source fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef silver fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef gold fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef ml fill:#e0f2f1,stroke:#004d40,stroke-width:2px,stroke-dasharray: 5 5;

    subgraph Sources [Bronze / Raw]
        RC[raw_customers]:::source
        RS[raw_subscriptions]:::source
        BM[fct_budget_monthly]:::source
        DC[dim_calendar]:::source
        RF[raw_forecast]:::source
    end

    subgraph Silver [Transformation]
        ISM[int_subscription_months]:::silver
        SB[stg_budget]:::silver
    end

    subgraph Gold [Marts]
        MFM[mart_finance_monthly]:::gold
        MFI[mart_forecast_input]:::gold
        MCR[mart_consolidated_reporting]:::gold
    end
    
    subgraph Agent [ML Agent]
        PY[Forecast Engine]:::ml
    end

    RC --> ISM
    RS --> ISM
    DC --> ISM
    BM --> SB
    
    ISM --> MFM
    SB --> MFM
    
    MFM --> MFI
    MFI --> PY
    PY -->|Writes Back| RF
    
    MFM --> MCR
    RF --> MCR
```

## 🛠 Tech Stack
-   **Code**: Python 3.11
-   **Database**: DuckDB (OLAP)
-   **Transformations**: dbt (Data Build Tool)
-   **ML/Forecasting**: Facebook Prophet
-   **Visualization**: Streamlit & Plotly Express

## 🚀 Quick Start

1.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Simulation Engine**
    ```bash
    # Extracts contract, runs simulation, builds dbt models, runs forecast
    python generator.py && cd dbt_financial && dbt run && cd .. && python forecast_model.py
    ```

3.  **Launch the Dashboard**
    ```bash
    streamlit run dashboard.py
    ```

---
*Created as a demonstration of Agentic Engineering capabilities.*
