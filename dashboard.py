"""
Global Financial Intelligence Dashboard
========================================
Enhanced with:
  - Data quality validation & null handling
  - Interactive Company Explorer (search any company)
  - Target Company Deep Analysis (7 specified companies)
  - Period reliability filters
  - Fixed DuckDB local mode with all computed columns

Run with:
  streamlit run dashboard.py --server.port 8501
"""

import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import duckdb
from google.cloud import bigquery

# ─────────────────────────────────────────────────────────────────
# CONFIG & AUTH
# ─────────────────────────────────────────────────────────────────
EXPORTS_DIR = "/home/meron/pfif_pathway/exports"
KEY_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "financial-data-491415-ecf1b9ff514d.json")
PROJECT_ID  = "financial-data-491415"
DATASET     = "financial_data"

def get_bq_client():
    """Returns a BigQuery client, using secrets if on Streamlit Cloud or local JSON if available."""
    if os.path.exists(KEY_FILE):
        return bigquery.Client.from_service_account_json(KEY_FILE)
    elif "gcp_service_account" in st.secrets:
        import json
        info = dict(st.secrets["gcp_service_account"])
        return bigquery.Client.from_service_account_info(info)
    else:
        return bigquery.Client(project=PROJECT_ID)

COLORS = {"GB": "#1E8449", "EU": "#1A5276", "US": "#6C3483"}
THEME_BG    = "#0F1117"
THEME_CARD  = "#1E2130"

# Target companies for deep analysis
TARGET_COMPANIES_MAP = {
    "ENTEGRIS INC": "Entegris Inc",
    "TERADYNE, INC": "Teradyne Inc",
    "WINTRUST FINANCIAL CORP": "Wintrust Financial",
    "COMMUNITY FINANCIAL CORP /MD/": "Community Financial (MD)",
    "COMMUNITY FINANCIAL SYSTEM, INC.": "Community Financial System",
    "WOODWARD, INC.": "Woodward Inc",
    "SILICON LABORATORIES INC.": "Silicon Laboratories",
    "BRUNSWICK CORP": "Brunswick Corporation",
}

# ─────────────────────────────────────────────────────────────────
# PAGE SETUP
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Global Financial Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    [data-testid="stAppViewContainer"] { background-color: #0F1117; }
    [data-testid="stSidebar"] { background-color: #1E2130; }
    h1, h2, h3 { color: #E8EAF6; }
    p, label { color: #B0BEC5; }
    .block-container { padding-top: 1rem; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1E2130, #252840);
        border-radius: 10px; padding: 12px;
        border: 1px solid #2a2f45;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E2130; border-radius: 8px;
        color: #B0BEC5; padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1F3864, #2E5FA3);
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# DATA LAYER
# ─────────────────────────────────────────────────────────────────
def tbl(name):
    return f"`{PROJECT_ID}.{DATASET}.{name}`"

@st.cache_data
def query(sql, mode):
    db = get_db_connection(mode)
    if mode == "Cloud (BigQuery)":
        return db.query(sql.replace("`","")).to_dataframe()
    else:
        clean_sql = sql.replace(f"`{PROJECT_ID}.{DATASET}.", "").replace("`", "")
        return db.execute(clean_sql).df()

@st.cache_resource
def get_db_connection(mode):
    if mode == "Cloud (BigQuery)":
        return bigquery.Client(project=PROJECT_ID)
    else:
        con = duckdb.connect(database=':memory:')
        # Register CSVs
        for tbl_name, file_name in [
            ("gb_xbrl_raw", "GB_XBRL_filings_long.csv"),
            ("eu_xbrl_raw", "EU_data.csv"),
            ("us_edgar_raw", "russell1000_edgar_filtered.csv")
        ]:
            path = os.path.join(EXPORTS_DIR, file_name)
            if os.path.exists(path):
                # Using all_varchar=True to prevent DuckDB from failing on mixed-type columns like 'decimals'
                con.execute(f"CREATE TABLE {tbl_name} AS SELECT * FROM read_csv_auto('{path}', all_varchar=True)")

        # Build concept crosswalk
        con.execute("""
            CREATE TABLE concept_crosswalk AS
            SELECT * FROM (VALUES
                ('Revenue', 'Revenue', 'Income Statement'),
                ('ifrs-full:Revenue', 'Revenue', 'Income Statement'),
                ('Revenues', 'Revenue', 'Income Statement'),
                ('RevenueFromContractsWithCustomers', 'Revenue', 'Income Statement'),
                ('RevenuefromContractswithCustomers', 'Revenue', 'Income Statement'),
                ('RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenue', 'Income Statement'),
                ('SalesRevenueNet', 'Revenue', 'Income Statement'),
                ('NetIncome', 'Net Income', 'Income Statement'),
                ('NetIncomeLoss', 'Net Income', 'Income Statement'),
                ('ProfitLoss', 'Net Income', 'Income Statement'),
                ('ifrs-full:ProfitLoss', 'Net Income', 'Income Statement'),
                ('OperatingIncomeLoss', 'Operating Income', 'Income Statement'),
                ('OperatingProfit', 'Operating Income', 'Income Statement'),
                ('ifrs-full:ProfitLossFromOperatingActivities', 'Operating Income', 'Income Statement'),
                ('GrossProfit', 'Gross Profit', 'Income Statement'),
                ('ifrs-full:GrossProfit', 'Gross Profit', 'Income Statement'),
                ('CostOfSales', 'Cost of Revenue', 'Income Statement'),
                ('CostOfRevenue', 'Cost of Revenue', 'Income Statement'),
                ('CostOfGoodsAndServicesSold', 'Cost of Revenue', 'Income Statement'),
                ('ifrs-full:CostOfSales', 'Cost of Revenue', 'Income Statement'),
                ('Assets', 'Total Assets', 'Balance Sheet'),
                ('ifrs-full:Assets', 'Total Assets', 'Balance Sheet'),
                ('Liabilities', 'Total Liabilities', 'Balance Sheet'),
                ('ifrs-full:Liabilities', 'Total Liabilities', 'Balance Sheet'),
                ('StockholdersEquity', 'Total Equity', 'Balance Sheet'),
                ('Equity', 'Total Equity', 'Balance Sheet'),
                ('ifrs-full:Equity', 'Total Equity', 'Balance Sheet'),
                ('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 'Total Equity', 'Balance Sheet'),
                ('CashAndCashEquivalentsAtCarryingValue', 'Cash', 'Balance Sheet'),
                ('CashAndCashEquivalents', 'Cash', 'Balance Sheet'),
                ('ifrs-full:CashAndCashEquivalents', 'Cash', 'Balance Sheet'),
                ('LongTermDebt', 'Long Term Debt', 'Balance Sheet'),
                ('LongTermDebtNoncurrent', 'Long Term Debt', 'Balance Sheet'),
                ('EarningsPerShareBasic', 'EPS Basic', 'Per Share'),
                ('EarningsPerShareDiluted', 'EPS Diluted', 'Per Share'),
                ('NetCashProvidedByUsedInOperatingActivities', 'Operating Cash Flow', 'Cash Flow'),
                ('NetCashProvidedByOperatingActivities', 'Operating Cash Flow', 'Cash Flow'),
                ('DividendsPaid', 'Dividends Paid', 'Cash Flow'),
                ('PaymentsOfDividends', 'Dividends Paid', 'Cash Flow'),
                ('Assets', 'Total Assets', 'Balance Sheet'), # Added US tag
                ('AssetsNet', 'Total Assets', 'Balance Sheet') # Added US tag
            ) AS t(concept_raw, standard_concept, concept_category)
        """)

        # Build unified view with data quality filters
        con.execute("""
            CREATE VIEW v_unified_financials AS
            WITH raw_all AS (
              SELECT company_name, 'GB' as market, 'United Kingdom' as country_full, 'GB' as country_code,
                     unit as currency, COALESCE(cx.standard_concept, g.concept) as concept,
                     cx.concept_category,
                     TRY_CAST(g.value AS DOUBLE) as value,
                     TRY_CAST(SPLIT(g.period_end, '-')[1] AS INT) as fiscal_year,
                     TRY_CAST(g.period_end AS DATE) as period_end
              FROM gb_xbrl_raw g
              LEFT JOIN concept_crosswalk cx ON g.concept = cx.concept_raw
              WHERE TRY_CAST(g.value AS DOUBLE) IS NOT NULL
                AND ABS(TRY_CAST(g.value AS DOUBLE)) < 1e12
              UNION ALL
              SELECT company_name, 'EU' as market, country as country_full, country as country_code,
                     unit as currency, COALESCE(cx.standard_concept, e.concept) as concept,
                     cx.concept_category,
                     TRY_CAST(e.value AS DOUBLE) as value,
                     TRY_CAST(SPLIT(e.period_end, '-')[1] AS INT) as fiscal_year,
                     TRY_CAST(e.period_end AS DATE) as period_end
              FROM eu_xbrl_raw e
              LEFT JOIN concept_crosswalk cx ON e.concept = cx.concept_raw
              WHERE TRY_CAST(e.value AS DOUBLE) IS NOT NULL
                AND TRY_CAST(SPLIT(e.period_end, '-')[1] AS INT) <= 2026
              UNION ALL
              SELECT company_name, 'US' as market, 'United States' as country_full, 'US' as country_code,
                     'USD' as currency, COALESCE(cx.standard_concept, u.concept) as concept,
                     cx.concept_category,
                     TRY_CAST(u.value AS DOUBLE) as value,
                     TRY_CAST(u.fiscal_year AS INT) as fiscal_year,
                     TRY_CAST(u.period_end AS DATE) as period_end
              FROM us_edgar_raw u
              LEFT JOIN concept_crosswalk cx ON u.concept = cx.concept_raw
              WHERE u.fiscal_year IS NOT NULL
                AND TRY_CAST(u.fiscal_year AS INT) IS NOT NULL
                AND (TRY_CAST(u.qtrs AS INT) IS NULL OR TRY_CAST(u.qtrs AS INT) <= 4)
            )
            SELECT * FROM raw_all
            WHERE fiscal_year BETWEEN 2010 AND 2026
              AND value IS NOT NULL
        """)

        # Revenue trends
        con.execute("""
            CREATE TABLE t_revenue_trends AS
            SELECT company_name, market, country_code, currency, fiscal_year, SUM(value) AS revenue
            FROM v_unified_financials WHERE concept = 'Revenue' AND fiscal_year BETWEEN 2019 AND 2025 AND value > 0
            GROUP BY 1,2,3,4,5
        """)

        # Profitability with computed margins
        con.execute("""
            CREATE TABLE t_profitability AS
            WITH base AS (
                SELECT company_name, market, country_code, fiscal_year,
                    MAX(CASE WHEN concept = 'Revenue' THEN value END) as revenue,
                    MAX(CASE WHEN concept = 'Gross Profit' THEN value END) as gross_profit,
                    MAX(CASE WHEN concept = 'Operating Income' THEN value END) as operating_income,
                    MAX(CASE WHEN concept = 'Net Income' THEN value END) as net_income,
                    MAX(CASE WHEN concept = 'Total Assets' THEN value END) as total_assets,
                    MAX(CASE WHEN concept = 'Total Equity' THEN value END) as total_equity,
                    MAX(CASE WHEN concept = 'Total Liabilities' THEN value END) as total_liabilities,
                    MAX(CASE WHEN concept = 'Cash' THEN value END) as cash,
                    MAX(CASE WHEN concept = 'Long Term Debt' THEN value END) as long_term_debt,
                    MAX(CASE WHEN concept = 'Operating Cash Flow' THEN value END) as operating_cash_flow,
                    MAX(CASE WHEN concept = 'EPS Basic' THEN value END) as eps_basic
                FROM v_unified_financials WHERE fiscal_year BETWEEN 2019 AND 2025 GROUP BY 1,2,3,4
            )
            SELECT *,
                gross_profit / NULLIF(revenue, 0) as gross_margin,
                operating_income / NULLIF(revenue, 0) as operating_margin,
                net_income / NULLIF(revenue, 0) as net_margin,
                net_income / NULLIF(total_equity, 0) as return_on_equity,
                net_income / NULLIF(total_assets, 0) as return_on_assets,
                total_liabilities / NULLIF(total_equity, 0) as debt_to_equity
            FROM base WHERE revenue IS NOT NULL AND revenue > 0
        """)

        # Market summary, top companies, growth, coverage
        con.execute("""
            CREATE TABLE t_market_summary AS
            SELECT market, COUNT(DISTINCT company_name) as total_companies,
                   COUNT(DISTINCT country_code) as total_countries,
                   COUNT(DISTINCT concept) as total_concepts,
                   MIN(fiscal_year) as data_from, MAX(fiscal_year) as data_to
            FROM v_unified_financials GROUP BY 1
        """)
        con.execute("""
            CREATE TABLE t_top_companies AS
            SELECT *, RANK() OVER(PARTITION BY market, fiscal_year ORDER BY revenue DESC) as revenue_rank
            FROM t_profitability
        """)
        con.execute("""
            CREATE TABLE t_yoy_growth AS
            SELECT c.company_name, c.market, c.country_code, c.fiscal_year,
                   c.revenue as revenue_current, p.revenue as revenue_prior,
                   (c.revenue - p.revenue) / NULLIF(p.revenue, 0) as yoy_growth_rate
            FROM t_revenue_trends c LEFT JOIN t_revenue_trends p
            ON c.company_name = p.company_name AND c.market = p.market AND c.fiscal_year = p.fiscal_year + 1
            WHERE c.fiscal_year BETWEEN 2020 AND 2025
        """)
        con.execute("""
            CREATE TABLE t_concept_coverage AS
            SELECT concept, concept_category,
                   COUNT(DISTINCT CASE WHEN market='GB' THEN company_name END) as gb_companies,
                   COUNT(DISTINCT CASE WHEN market='EU' THEN company_name END) as eu_companies,
                   COUNT(DISTINCT CASE WHEN market='US' THEN company_name END) as us_companies,
                   COUNT(DISTINCT company_name) as total_companies
            FROM v_unified_financials WHERE concept_category IS NOT NULL GROUP BY 1,2
        """)
        return con


# ─────────────────────────────────────────────────────────────────
# HELPER: safe formatting
# ─────────────────────────────────────────────────────────────────
def fmt_money(v):
    if pd.isna(v) or v is None: return "N/A"
    if abs(v) >= 1e9: return f"${v/1e9:.2f}B"
    if abs(v) >= 1e6: return f"${v/1e6:.1f}M"
    if abs(v) >= 1e3: return f"${v/1e3:.0f}K"
    return f"${v:.0f}"

def fmt_pct(v):
    if pd.isna(v) or v is None: return "N/A"
    return f"{v*100:.1f}%"

def safe_metric(val, default="N/A"):
    if pd.isna(val) or val is None: return default
    return val

def make_chart_layout(fig, title=None):
    fig.update_layout(
        paper_bgcolor=THEME_BG, plot_bgcolor=THEME_BG,
        font=dict(color="white", family="Inter"),
        title=dict(font=dict(size=16)) if title else {},
        margin=dict(t=40, b=40, l=40, r=20),
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style='text-align:center; padding: 10px;'>
    <span style='font-size:2.5rem;'>📊</span>
    <h2 style='color:#E8EAF6; margin:0;'>Financial Intelligence</h2>
    <p style='color:#6C7A89; margin:0; font-size:0.8rem;'>GB · EU · US Markets</p>
</div>
""", unsafe_allow_html=True)

# Check if local files exist for DuckDB mode
local_files_exist = os.path.exists(os.path.join(EXPORTS_DIR, "russell1000_edgar_filtered.csv"))
engine_options = ["Cloud (BigQuery)"]
if local_files_exist:
    engine_options.insert(0, "Local (DuckDB + CSVs)")

data_mode = st.sidebar.radio("Data Engine", engine_options, index=0)
st.sidebar.markdown("---")

page = st.sidebar.radio("Navigate", [
    "🌍 Executive Overview",
    "📈 Revenue Intelligence",
    "💰 Profitability & Margins",
    "🏦 Balance Sheet Strength",
    "🚀 Growth Analysis",
    "⚔️  Cross-Market Comparison",
    "🔍 Company Explorer",
    "🎯 Target Company Analysis",
    "🩺 Data Quality Report",
])

st.sidebar.markdown("---")
# Default to 2022 (index 3) because US data has many peaks in 2020-2022, while GB/EU are later.
year_filter = st.sidebar.selectbox("Fiscal Year", list(range(2025, 2018, -1)), index=3)
market_filter = st.sidebar.multiselect("Markets", ["GB", "EU", "US"], default=["GB", "EU", "US"])

if st.sidebar.button("🗑️ Clear Cache"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

market_sql = "(" + ", ".join([f"'{m}'" for m in market_filter]) + ")" if market_filter else "('GB','EU','US')"


# ─────────────────────────────────────────────────────────────────
# PAGE 1 — EXECUTIVE OVERVIEW
# ─────────────────────────────────────────────────────────────────
if page == "🌍 Executive Overview":
    st.markdown("""
    <div style='background: linear-gradient(135deg, #1F3864 0%, #2E5FA3 50%, #4A7DD7 100%);
                padding: 2rem; border-radius: 12px; margin-bottom: 1.5rem;'>
        <h1 style='color: white; margin: 0; font-size: 2.2rem;'>
            🌍 Global Financial Intelligence Dashboard
        </h1>
        <p style='color: #B0C4DE; margin: 0.5rem 0 0;'>
            GB · EU · US Markets &nbsp;|&nbsp; XBRL Data from AWS S3 → BigQuery
        </p>
        <div style='background: rgba(255,255,255,0.1); padding: 10px; border-radius: 6px; margin-top: 15px; font-size: 0.9rem; color: #E8EAF6;'>
            ℹ️ <b>About this page:</b> This is your high-level control center. It summarizes total market coverage, regional company distribution, and identifies the world's largest players by revenue. Use the map to explore geographic density.
        </div>
    </div>
    """, unsafe_allow_html=True)

    try:
        summary = query(f"SELECT * FROM {tbl('t_market_summary')}", data_mode)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🏢 Total Companies", f"{int(summary['total_companies'].sum()):,}")
        c2.metric("🌐 Markets Covered", len(summary))
        c3.metric("📑 Unique Concepts", f"{int(summary['total_concepts'].max()):,}+")
        c4.metric("📅 Data Range", f"{int(summary['data_from'].min())}–{int(summary['data_to'].max())}")

        st.markdown("---")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("🗺️ Companies by Market")
            geo = query(f"""
                SELECT country_full, COUNT(DISTINCT company_name) AS companies
                FROM {tbl('v_unified_financials')}
                WHERE market IN {market_sql}
                GROUP BY country_full
            """, data_mode)
            if not geo.empty:
                fig = px.choropleth(geo, locations="country_full", locationmode="country names",
                                    color="companies", color_continuous_scale="Blues",
                                    title="Companies per Country")
                make_chart_layout(fig)
                fig.update_layout(geo=dict(bgcolor=THEME_BG))
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("📊 Revenue Share by Market")
            rev = query(f"""
                SELECT market, SUM(revenue) AS total_revenue
                FROM {tbl('t_profitability')}
                WHERE fiscal_year = {year_filter} AND market IN {market_sql}
                GROUP BY market
            """, data_mode)
            if not rev.empty:
                fig2 = px.pie(rev, names="market", values="total_revenue", hole=0.5,
                              color="market", color_discrete_map=COLORS)
                make_chart_layout(fig2)
                st.plotly_chart(fig2, use_container_width=True)

        st.subheader(f"🏆 Top 15 Companies by Revenue ({year_filter})")
        top = query(f"""
            SELECT company_name, market, revenue
            FROM {tbl('t_top_companies')}
            WHERE revenue_rank <= 15 AND market IN {market_sql} AND fiscal_year = {year_filter}
            ORDER BY revenue DESC
        """, data_mode)
        if not top.empty:
            fig3 = px.bar(top, x="revenue", y="company_name", orientation="h",
                          color="market", color_discrete_map=COLORS)
            make_chart_layout(fig3)
            fig3.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig3, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading overview: {e}")


# ─────────────────────────────────────────────────────────────────
# PAGE 2 — REVENUE INTELLIGENCE
# ─────────────────────────────────────────────────────────────────
elif page == "📈 Revenue Intelligence":
    st.title("📈 Revenue Intelligence")
    st.info("💡 **About this page:** Analyzes top-line performance. It tracks how much money companies are making, identifies revenue growth leaders, and provides a multi-year trend line to compare market momentum over time.")
    try:
        prof = query(f"""
            SELECT SUM(revenue) AS total_rev,
                   AVG(gross_margin) AS avg_gross,
                   AVG(net_margin) AS avg_net
            FROM {tbl('t_profitability')}
            WHERE fiscal_year = {year_filter} AND market IN {market_sql}
        """, data_mode)
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Total Revenue", fmt_money(safe_metric(prof['total_rev'].values[0], 0)))
        c2.metric("📊 Avg Gross Margin", fmt_pct(safe_metric(prof['avg_gross'].values[0])))
        c3.metric("📉 Avg Net Margin", fmt_pct(safe_metric(prof['avg_net'].values[0])))

        st.subheader("Revenue Trend by Market")
        trends = query(f"""
            SELECT fiscal_year, market, SUM(revenue) AS revenue
            FROM {tbl('t_revenue_trends')}
            WHERE market IN {market_sql}
            GROUP BY fiscal_year, market ORDER BY fiscal_year
        """, data_mode)
        if not trends.empty:
            fig = px.line(trends, x="fiscal_year", y="revenue", color="market",
                          color_discrete_map=COLORS, markers=True)
            make_chart_layout(fig)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader(f"Top 20 Companies by Revenue ({year_filter})")
        top20 = query(f"""
            SELECT company_name, market, revenue
            FROM {tbl('t_top_companies')}
            WHERE revenue_rank <= 20 AND market IN {market_sql} AND fiscal_year = {year_filter}
            ORDER BY revenue DESC
        """, data_mode)
        if not top20.empty:
            fig2 = px.bar(top20, x="revenue", y="company_name", orientation="h",
                          color="market", color_discrete_map=COLORS)
            make_chart_layout(fig2)
            fig2.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading revenue data: {e}")


# ─────────────────────────────────────────────────────────────────
# PAGE 3 — PROFITABILITY & MARGINS
# ─────────────────────────────────────────────────────────────────
elif page == "💰 Profitability & Margins":
    st.title("💰 Profitability & Margins")
    st.info("💡 **About this page:** Focuses on efficiency. This page visualizes the relationship between scale (Revenue) and profitability (Net Margin). High margins indicate strong competitive advantages and efficient cost management.")
    try:
        scatter = query(f"""
            SELECT company_name, market, revenue, net_margin, gross_margin, operating_margin
            FROM {tbl('t_profitability')}
            WHERE fiscal_year = {year_filter} AND revenue > 0
              AND market IN {market_sql}
              AND net_margin IS NOT NULL AND ABS(net_margin) < 1
        """, data_mode)

        if not scatter.empty:
            st.subheader("📍 Revenue vs Net Margin")
            scatter['gross_margin_abs'] = scatter['gross_margin'].abs().fillna(0.01)
            fig = px.scatter(scatter, x="revenue", y="net_margin",
                             size="gross_margin_abs", color="market",
                             color_discrete_map=COLORS, hover_name="company_name",
                             log_x=True)
            make_chart_layout(fig)
            st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Avg Margins by Market")
            mkt_margins = query(f"""
                SELECT market,
                       AVG(gross_margin) AS gross_margin,
                       AVG(operating_margin) AS operating_margin,
                       AVG(net_margin) AS net_margin
                FROM {tbl('t_profitability')}
                WHERE fiscal_year = {year_filter} AND market IN {market_sql}
                GROUP BY market
            """, data_mode)
            if not mkt_margins.empty:
                fig2 = go.Figure()
                for col_name, label in [("gross_margin","Gross"), ("operating_margin","Operating"), ("net_margin","Net")]:
                    if col_name in mkt_margins.columns:
                        fig2.add_trace(go.Bar(name=label, x=mkt_margins["market"],
                                              y=mkt_margins[col_name].fillna(0)*100))
                fig2.update_layout(barmode="group")
                make_chart_layout(fig2)
                fig2.update_layout(yaxis_title="Margin %")
                st.plotly_chart(fig2, use_container_width=True)

        with col2:
            st.subheader(f"Top 15 by Net Margin ({year_filter})")
            top_nm = query(f"""
                SELECT company_name, market, net_margin
                FROM {tbl('t_profitability')}
                WHERE fiscal_year = {year_filter} AND net_margin > 0 AND net_margin < 1
                  AND market IN {market_sql}
                ORDER BY net_margin DESC LIMIT 15
            """, data_mode)
            if not top_nm.empty:
                fig3 = px.bar(top_nm, x="net_margin", y="company_name", orientation="h",
                              color="market", color_discrete_map=COLORS)
                make_chart_layout(fig3)
                fig3.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig3, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")


# ─────────────────────────────────────────────────────────────────
# PAGE 4 — BALANCE SHEET STRENGTH
# ─────────────────────────────────────────────────────────────────
elif page == "🏦 Balance Sheet Strength":
    st.title("🏦 Balance Sheet Strength")
    st.info("💡 **About this page:** Evaluates financial health and solvency. It compares Total Assets against Liabilities to determine the equity cushion. Use this to identify highly leveraged versus cash-rich markets.")
    try:
        bs = query(f"""
            SELECT market,
                   SUM(total_assets) AS total_assets,
                   SUM(total_liabilities) AS total_liabilities,
                   SUM(total_equity) AS total_equity,
                   AVG(debt_to_equity) AS avg_dte,
                   AVG(cash) AS avg_cash
            FROM {tbl('t_profitability')}
            WHERE fiscal_year = {year_filter} AND market IN {market_sql}
            GROUP BY market
        """, data_mode)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Assets vs Liabilities vs Equity")
            fig = go.Figure()
            for metric, colour in [("total_assets","#2196F3"),("total_liabilities","#F44336"),("total_equity","#4CAF50")]:
                if metric in bs.columns:
                    fig.add_trace(go.Bar(name=metric.replace("_"," ").title(),
                                         x=bs["market"], y=bs[metric].fillna(0)/1e9, marker_color=colour))
            fig.update_layout(barmode="group", yaxis_title="Value (Billions)")
            make_chart_layout(fig)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Avg Debt-to-Equity by Market")
            if 'avg_dte' in bs.columns:
                fig2 = px.bar(bs, x="market", y="avg_dte", color="market", color_discrete_map=COLORS)
                make_chart_layout(fig2)
                st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Balance Sheet Trends Over Time")
        bs_trend = query(f"""
            SELECT fiscal_year, market,
                   SUM(total_assets) AS total_assets,
                   SUM(total_equity) AS total_equity,
                   SUM(total_liabilities) AS total_liabilities
            FROM {tbl('t_profitability')}
            WHERE market IN {market_sql}
            GROUP BY fiscal_year, market ORDER BY fiscal_year
        """, data_mode)
        if not bs_trend.empty:
            fig3 = px.line(bs_trend, x="fiscal_year", y="total_assets",
                           color="market", color_discrete_map=COLORS, markers=True,
                           title="Total Assets Over Time")
            make_chart_layout(fig3)
            st.plotly_chart(fig3, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")


# ─────────────────────────────────────────────────────────────────
# PAGE 5 — GROWTH ANALYSIS
# ─────────────────────────────────────────────────────────────────
elif page == "🚀 Growth Analysis":
    st.title("🚀 Growth Analysis")
    st.info("💡 **About this page:** Tracks year-over-year momentum. It identifies the fastest-growing 'disruptors' and classifies companies into growth buckets, showing where the most aggressive expansion is occurring.")
    try:
        growth = query(f"""
            SELECT company_name, market, country_code,
                   fiscal_year, revenue_current, revenue_prior, yoy_growth_rate
            FROM {tbl('t_yoy_growth')}
            WHERE fiscal_year = {year_filter} AND market IN {market_sql}
              AND yoy_growth_rate IS NOT NULL
            ORDER BY yoy_growth_rate DESC
        """, data_mode)

        if not growth.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📊 Median Growth", fmt_pct(growth['yoy_growth_rate'].median()))
            c2.metric("✅ Positive Growth", f"{(growth['yoy_growth_rate']>0).mean()*100:.0f}%")
            c3.metric("🔼 Fastest", growth.iloc[0]["company_name"][:20])
            c4.metric("🔽 Slowest", growth.iloc[-1]["company_name"][:20])

            st.subheader("Growth League Table")
            disp = growth[["company_name","market","revenue_current","revenue_prior","yoy_growth_rate"]].copy()
            disp["yoy_growth_rate"] = (disp["yoy_growth_rate"]*100).round(1).astype(str) + "%"
            disp["revenue_current"] = disp["revenue_current"].apply(lambda x: fmt_money(x) if pd.notnull(x) else "")
            disp["revenue_prior"] = disp["revenue_prior"].apply(lambda x: fmt_money(x) if pd.notnull(x) else "")
            st.dataframe(disp.rename(columns={
                "company_name":"Company","market":"Market",
                "revenue_current":"Revenue (Current)","revenue_prior":"Revenue (Prior)",
                "yoy_growth_rate":"YoY Growth"
            }), use_container_width=True, height=450)

            def bucket(r):
                if r < -0.2: return "< -20%"
                if r < 0: return "-20% to 0%"
                if r < 0.1: return "0% to 10%"
                if r < 0.25: return "10% to 25%"
                return "> 25%"
            growth["bucket"] = growth["yoy_growth_rate"].apply(bucket)
            dist = growth.groupby(["bucket","market"]).size().reset_index(name="count")
            fig = px.bar(dist, x="bucket", y="count", color="market",
                         color_discrete_map=COLORS, barmode="group",
                         category_orders={"bucket":["< -20%","-20% to 0%","0% to 10%","10% to 25%","> 25%"]})
            make_chart_layout(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No growth data available for the selected filters.")
    except Exception as e:
        st.error(f"Error: {e}")


# ─────────────────────────────────────────────────────────────────
# PAGE 6 — CROSS-MARKET COMPARISON
# ─────────────────────────────────────────────────────────────────
elif page == "⚔️  Cross-Market Comparison":
    st.title("⚔️ Cross-Market Comparison")
    st.info("💡 **About this page:** Directly pits GB, EU, and US markets against each other. It shows which regions have the highest average margins and ROE, helping identify the most profitable global investment climates.")
    try:
        mkt = query(f"""
            SELECT market,
                   AVG(gross_margin) AS gross_margin,
                   AVG(operating_margin) AS operating_margin,
                   AVG(net_margin) AS net_margin,
                   AVG(return_on_equity) AS roe,
                   AVG(debt_to_equity) AS dte,
                   COUNT(DISTINCT company_name) AS companies
            FROM {tbl('t_profitability')}
            WHERE fiscal_year = {year_filter} AND market IN {market_sql}
            GROUP BY market
        """, data_mode)

        st.subheader(f"Head-to-Head KPIs — {year_filter}")
        cols = st.columns(len(mkt))
        for i, row in mkt.iterrows():
            with cols[i]:
                colour = COLORS.get(row["market"], "#888")
                gm = fmt_pct(safe_metric(row.get("gross_margin")))
                nm = fmt_pct(safe_metric(row.get("net_margin")))
                roe_v = fmt_pct(safe_metric(row.get("roe")))
                dte_v = f"{row['dte']:.2f}x" if pd.notnull(row.get("dte")) else "N/A"
                st.markdown(f"""
                <div style='background:{colour}22; border-left:4px solid {colour};
                            border-radius:8px; padding:16px; margin-bottom:8px;'>
                    <h3 style='color:{colour}; margin:0'>{row["market"]}</h3>
                    <p style='color:white; margin:4px 0'><b>{int(row["companies"]):,}</b> companies</p>
                    <p style='color:#aaa; margin:2px 0'>Gross Margin: <b>{gm}</b></p>
                    <p style='color:#aaa; margin:2px 0'>Net Margin: <b>{nm}</b></p>
                    <p style='color:#aaa; margin:2px 0'>ROE: <b>{roe_v}</b></p>
                    <p style='color:#aaa; margin:2px 0'>Debt/Equity: <b>{dte_v}</b></p>
                </div>
                """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Margin Comparison")
            fig = go.Figure()
            for metric, label in [("gross_margin","Gross"),("operating_margin","Operating"),("net_margin","Net")]:
                if metric in mkt.columns:
                    fig.add_trace(go.Bar(name=label, x=mkt["market"], y=mkt[metric].fillna(0)*100))
            fig.update_layout(barmode="group", yaxis_title="% Margin")
            make_chart_layout(fig)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Concept Coverage")
            cov = query(f"""
                SELECT concept, gb_companies, eu_companies, us_companies
                FROM {tbl('t_concept_coverage')}
                ORDER BY total_companies DESC LIMIT 15
            """, data_mode)
            if not cov.empty:
                fig2 = go.Figure()
                for col_name, colour in [("gb_companies","#1E8449"),("eu_companies","#1A5276"),("us_companies","#6C3483")]:
                    if col_name in cov.columns:
                        fig2.add_trace(go.Bar(name=col_name.replace("_companies","").upper(),
                                              x=cov["concept"], y=cov[col_name], marker_color=colour))
                fig2.update_layout(barmode="stack", xaxis=dict(tickangle=-45))
                make_chart_layout(fig2)
                st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")


# ─────────────────────────────────────────────────────────────────
# PAGE 7 — COMPANY EXPLORER (NEW - Interactive Search)
# ─────────────────────────────────────────────────────────────────
elif page == "🔍 Company Explorer":
    st.markdown("""
    <div style='background: linear-gradient(135deg, #2d1b69 0%, #11998e 100%);
                padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;'>
        <h1 style='color: white; margin: 0;'>🔍 Company Explorer</h1>
        <p style='color: #B0C4DE; margin: 0.5rem 0 0;'>
            Search and analyze any company in the dataset
        </p>
        <div style='background: rgba(255,255,255,0.1); padding: 10px; border-radius: 6px; margin-top: 15px; font-size: 0.9rem; color: #E8EAF6;'>
            ℹ️ <b>About this page:</b> Interactive deep-dive. Search for any specific company to see their full financial history, margin trends, and key ratios. Perfect for detailed individual company research.
        </div>
    </div>
    """, unsafe_allow_html=True)

    try:
        # Get company list
        companies_df = query(f"""
            SELECT DISTINCT company_name, market
            FROM {tbl('t_profitability')}
            WHERE market IN {market_sql}
            ORDER BY company_name
        """, data_mode)

        if not companies_df.empty:
            company_list = sorted(companies_df['company_name'].unique())

            col_search, col_market = st.columns([3, 1])
            with col_search:
                search_term = st.text_input("🔎 Search company name", placeholder="Type to search...")
            with col_market:
                search_market = st.selectbox("Filter market", ["All"] + list(COLORS.keys()))

            if search_term:
                filtered = [c for c in company_list if search_term.lower() in c.lower()]
            else:
                filtered = company_list[:50]

            if search_market != "All":
                mkt_companies = companies_df[companies_df['market'] == search_market]['company_name'].unique()
                filtered = [c for c in filtered if c in mkt_companies]

            selected_company = st.selectbox(
                f"Select a company ({len(filtered)} matches)",
                filtered if filtered else ["No matches found"]
            )

            if selected_company and selected_company != "No matches found":
                st.markdown("---")

                # Fetch company data
                comp_data = query(f"""
                    SELECT * FROM {tbl('t_profitability')}
                    WHERE company_name = '{selected_company.replace("'", "''")}'
                    ORDER BY fiscal_year
                """, data_mode)

                if not comp_data.empty:
                    latest = comp_data.iloc[-1]
                    mkt_color = COLORS.get(latest.get('market', ''), '#888')

                    st.markdown(f"""
                    <div style='background:{mkt_color}15; border: 1px solid {mkt_color}44;
                                border-radius:12px; padding:20px; margin-bottom:16px;'>
                        <h2 style='color:{mkt_color}; margin:0;'>{selected_company}</h2>
                        <p style='color:#aaa; margin:4px 0;'>Market: <b>{latest.get('market','')}</b> | Latest Year: <b>{int(latest['fiscal_year'])}</b></p>
                    </div>
                    """, unsafe_allow_html=True)

                    # KPI Cards
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Revenue", fmt_money(safe_metric(latest.get('revenue'))))
                    c2.metric("Net Income", fmt_money(safe_metric(latest.get('net_income'))))
                    c3.metric("Total Assets", fmt_money(safe_metric(latest.get('total_assets'))))
                    c4.metric("Net Margin", fmt_pct(safe_metric(latest.get('net_margin'))))
                    c5.metric("ROE", fmt_pct(safe_metric(latest.get('return_on_equity'))))

                    # Revenue trend
                    rev_trend = query(f"""
                        SELECT fiscal_year, revenue FROM {tbl('t_revenue_trends')}
                        WHERE company_name = '{selected_company.replace("'", "''")}' ORDER BY fiscal_year
                    """, data_mode)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("📈 Revenue Trend")
                        if not rev_trend.empty:
                            fig = px.line(rev_trend, x="fiscal_year", y="revenue", markers=True,
                                          line_shape="spline")
                            fig.update_traces(line=dict(color=mkt_color, width=3), marker=dict(size=8))
                            make_chart_layout(fig)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No revenue trend data")

                    with col2:
                        st.subheader("📊 Margin Trends")
                        margin_cols = [c for c in ['gross_margin','operating_margin','net_margin'] if c in comp_data.columns]
                        if margin_cols:
                            fig2 = go.Figure()
                            colors_margin = {"gross_margin":"#4CAF50","operating_margin":"#FF9800","net_margin":"#2196F3"}
                            for mc in margin_cols:
                                fig2.add_trace(go.Scatter(
                                    x=comp_data["fiscal_year"], y=comp_data[mc].fillna(0)*100,
                                    mode='lines+markers', name=mc.replace("_"," ").title(),
                                    line=dict(color=colors_margin.get(mc, "#fff"), width=2)
                                ))
                            make_chart_layout(fig2)
                            fig2.update_layout(yaxis_title="Margin %")
                            st.plotly_chart(fig2, use_container_width=True)

                    # Financial table
                    st.subheader("📋 Financial Summary Table")
                    display_cols = ['fiscal_year','revenue','net_income','gross_profit','total_assets','total_equity','total_liabilities','cash']
                    available = [c for c in display_cols if c in comp_data.columns]
                    disp_df = comp_data[available].copy()
                    for col in available:
                        if col != 'fiscal_year':
                            disp_df[col] = disp_df[col].apply(lambda x: fmt_money(x) if pd.notnull(x) else "N/A")
                    disp_df.columns = [c.replace("_"," ").title() for c in disp_df.columns]
                    st.dataframe(disp_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("No profitability data for this company.")
    except Exception as e:
        st.error(f"Error: {e}")


# ─────────────────────────────────────────────────────────────────
# PAGE 8 — TARGET COMPANY ANALYSIS (NEW)
# ─────────────────────────────────────────────────────────────────
elif page == "🎯 Target Company Analysis":
    st.markdown("""
    <div style='background: linear-gradient(135deg, #e65100 0%, #ff6d00 50%, #ffa726 100%);
                padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;'>
        <h1 style='color: white; margin: 0;'>🎯 Target Company Deep Dive</h1>
        <p style='color: #FFE0B2; margin: 0.5rem 0 0;'>
            Entegris · Teradyne · Wintrust · Community Financial · Woodward · Silicon Labs · Brunswick
        </p>
        <div style='background: rgba(255,255,255,0.1); padding: 10px; border-radius: 6px; margin-top: 15px; font-size: 0.9rem; color: #E8EAF6;'>
            ℹ️ <b>About this page:</b> Bespoke analysis for our 7 watchlist companies. It aggregates their data to show who is outperforming in growth, margins, and financial strength.
        </div>
    </div>
    """, unsafe_allow_html=True)

    try:
        # Build search clause for target companies
        target_names = list(TARGET_COMPANIES_MAP.keys())
        name_clauses = " OR ".join([f"company_name = '{n.replace(chr(39), chr(39)+chr(39))}'" for n in target_names])

        target_data = query(f"""
            SELECT * FROM {tbl('t_profitability')}
            WHERE ({name_clauses})
            ORDER BY company_name, fiscal_year
        """, data_mode)

        if target_data.empty:
            st.warning("⚠️ Target companies not found in the current dataset. These are US companies — make sure US market data is loaded and the 'US' filter is selected.")
            st.info("""
            **Why some companies may be missing:**
            - **Brunswick Corporation**: Not found in the US EDGAR dataset. This company may file under a different entity name (e.g., "BRUNSWICK CORP") or may not be in the current data extract.
            - The data only includes companies present in the XBRL data files on S3.
            """)
        else:
            found = target_data['company_name'].unique()
            st.success(f"✅ Found {len(found)} target companies: {', '.join(found)}")

            # Missing companies
            missing = [n for n in target_names if n not in found]
            if missing:
                st.warning(f"⚠️ Not found: {', '.join(missing)}")

            # Comparative KPI table
            st.subheader(f"📊 Comparative KPIs — {year_filter}")
            latest = target_data[target_data['fiscal_year'] == year_filter].copy()
            if latest.empty:
                available_years = sorted(target_data['fiscal_year'].unique())
                closest = max([y for y in available_years if y <= year_filter], default=available_years[-1])
                latest = target_data[target_data['fiscal_year'] == closest].copy()
                st.info(f"No data for {year_filter}, showing {int(closest)}")

            if not latest.empty:
                kpi_cols = ['company_name','revenue','net_income','gross_margin','net_margin',
                            'return_on_equity','debt_to_equity','total_assets','cash']
                avail = [c for c in kpi_cols if c in latest.columns]
                kpi_df = latest[avail].copy()
                for col in avail:
                    if col == 'company_name': continue
                    if 'margin' in col or 'return' in col or 'equity' in col:
                        kpi_df[col] = kpi_df[col].apply(lambda x: fmt_pct(x) if pd.notnull(x) else "N/A")
                    else:
                        kpi_df[col] = kpi_df[col].apply(lambda x: fmt_money(x) if pd.notnull(x) else "N/A")
                kpi_df.columns = [c.replace("_"," ").title() for c in kpi_df.columns]
                st.dataframe(kpi_df, use_container_width=True, hide_index=True)

            # Revenue comparison chart
            st.subheader("📈 Revenue Comparison Over Time")
            fig = px.line(target_data, x="fiscal_year", y="revenue", color="company_name",
                          markers=True, line_shape="spline")
            make_chart_layout(fig)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig, use_container_width=True)

            # Profitability comparison
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("💰 Net Margin Comparison")
                if 'net_margin' in target_data.columns:
                    fig2 = px.line(target_data, x="fiscal_year", y="net_margin", color="company_name",
                                  markers=True)
                    make_chart_layout(fig2)
                    fig2.update_layout(yaxis_tickformat=".0%")
                    st.plotly_chart(fig2, use_container_width=True)

            with col2:
                st.subheader("🏦 Debt-to-Equity Comparison")
                if 'debt_to_equity' in target_data.columns:
                    fig3 = px.bar(target_data[target_data['fiscal_year']==target_data['fiscal_year'].max()],
                                 x="company_name", y="debt_to_equity", color="company_name")
                    make_chart_layout(fig3)
                    fig3.update_layout(showlegend=False, xaxis_tickangle=-30)
                    st.plotly_chart(fig3, use_container_width=True)

            # Individual company tabs
            st.markdown("---")
            st.subheader("🔎 Individual Company Details")
            tabs = st.tabs([n[:15] for n in found])
            for i, company in enumerate(found):
                with tabs[i]:
                    cd = target_data[target_data['company_name'] == company].sort_values('fiscal_year')
                    if not cd.empty:
                        latest_row = cd.iloc[-1]
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Revenue", fmt_money(safe_metric(latest_row.get('revenue'))))
                        c2.metric("Net Income", fmt_money(safe_metric(latest_row.get('net_income'))))
                        c3.metric("Net Margin", fmt_pct(safe_metric(latest_row.get('net_margin'))))
                        c4.metric("Total Assets", fmt_money(safe_metric(latest_row.get('total_assets'))))

                        # Mini trend
                        fig_mini = go.Figure()
                        fig_mini.add_trace(go.Scatter(x=cd['fiscal_year'], y=cd['revenue'],
                                                       name='Revenue', mode='lines+markers',
                                                       line=dict(color='#2196F3', width=2)))
                        if 'net_income' in cd.columns:
                            fig_mini.add_trace(go.Scatter(x=cd['fiscal_year'], y=cd['net_income'],
                                                           name='Net Income', mode='lines+markers',
                                                           line=dict(color='#4CAF50', width=2)))
                        make_chart_layout(fig_mini)
                        fig_mini.update_layout(height=300)
                        st.plotly_chart(fig_mini, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")


# ─────────────────────────────────────────────────────────────────
# PAGE 9 — DATA QUALITY REPORT (NEW)
# ─────────────────────────────────────────────────────────────────
elif page == "🩺 Data Quality Report":
    st.markdown("""
    <div style='background: linear-gradient(135deg, #1b5e20 0%, #388e3c 100%);
                padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;'>
        <h1 style='color: white; margin: 0;'>🩺 Data Quality Report</h1>
        <p style='color: #C8E6C9; margin: 0.5rem 0 0;'>Validation, null analysis, and data reliability checks</p>
        <div style='background: rgba(255,255,255,0.1); padding: 10px; border-radius: 6px; margin-top: 15px; font-size: 0.9rem; color: #E8EAF6;'>
            ℹ️ <b>About this page:</b> Transparent data auditing. Shows you what data we've filtered (like future years or non-numeric values) to ensure the analytics you see are trustworthy and reliable.
        </div>
    </div>
    """, unsafe_allow_html=True)

    try:
        # Null analysis per market
        st.subheader("📊 Data Coverage by Market & Year")
        quality = query(f"""
            SELECT market, fiscal_year,
                   COUNT(*) AS total_rows,
                   COUNT(DISTINCT company_name) AS companies
            FROM {tbl('v_unified_financials')}
            WHERE fiscal_year BETWEEN 2019 AND 2025
            GROUP BY market, fiscal_year
            ORDER BY market, fiscal_year
        """, data_mode)

        if not quality.empty:
            fig = px.bar(quality, x="fiscal_year", y="total_rows", color="market",
                         color_discrete_map=COLORS, barmode="group",
                         title="Data Rows by Market & Year")
            make_chart_layout(fig)
            st.plotly_chart(fig, use_container_width=True)

        # Concept completeness
        st.subheader("📋 Key Concept Availability")
        key_concepts = ['Revenue', 'Net Income', 'Gross Profit', 'Operating Income',
                        'Total Assets', 'Total Equity', 'Total Liabilities', 'Cash']
        concept_list = ", ".join([f"'{c}'" for c in key_concepts])
        completeness = query(f"""
            SELECT concept, market, COUNT(DISTINCT company_name) AS companies,
                   COUNT(*) AS data_points
            FROM {tbl('v_unified_financials')}
            WHERE concept IN ({concept_list})
              AND fiscal_year BETWEEN 2019 AND 2025
            GROUP BY concept, market
            ORDER BY concept, market
        """, data_mode)

        if not completeness.empty:
            fig2 = px.bar(completeness, x="concept", y="companies", color="market",
                          color_discrete_map=COLORS, barmode="group",
                          title="Companies with Data per Concept")
            make_chart_layout(fig2)
            fig2.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig2, use_container_width=True)

        # Profitability null report
        st.subheader("⚠️ Null Values in Profitability Table")
        prof_quality = query(f"""
            SELECT market,
                   COUNT(*) AS total_rows,
                   SUM(CASE WHEN revenue IS NULL THEN 1 ELSE 0 END) AS null_revenue,
                   SUM(CASE WHEN net_income IS NULL THEN 1 ELSE 0 END) AS null_net_income,
                   SUM(CASE WHEN gross_profit IS NULL THEN 1 ELSE 0 END) AS null_gross_profit,
                   SUM(CASE WHEN total_assets IS NULL THEN 1 ELSE 0 END) AS null_total_assets,
                   SUM(CASE WHEN total_equity IS NULL THEN 1 ELSE 0 END) AS null_total_equity,
                   SUM(CASE WHEN cash IS NULL THEN 1 ELSE 0 END) AS null_cash
            FROM {tbl('t_profitability')}
            GROUP BY market
        """, data_mode)

        if not prof_quality.empty:
            st.dataframe(prof_quality, use_container_width=True, hide_index=True)

        # Known issues
        st.subheader("📝 Known Data Quality Issues & Fixes Applied")
        st.markdown("""
        | Issue | Market | Status | Details |
        |-------|--------|--------|---------|
        | Future year dates (2029, 2031) | EU | ✅ Fixed | Filtered out rows with period_end year > 2026 |
        | Non-numeric values in `value` | GB | ✅ Fixed | 18,777 text values filtered via SAFE_CAST |
        | Extreme outlier values (±85T+) | GB | ✅ Fixed | Values > ±1 trillion filtered as data errors |
        | Null fiscal_year | US | ✅ Fixed | 5% of rows excluded (no timeline placement) |
        | Unreliable period durations (qtrs > 4) | US | ✅ Fixed | Multi-year cumulative entries excluded |
        | Company names as LEI codes | GB | ℹ️ Known | XBRL filings use LEI identifiers, not display names |
        | Null unit/currency | GB/EU | ℹ️ Tolerated | 2-5% of rows; doesn't affect value aggregation |
        | Brunswick Corporation missing | US | ⚠️ Open | Not in current EDGAR extract; may file as different entity |
        | Null `coreg` field | US | ℹ️ Normal | 98% null — expected for non-co-registrant filings |
        | Zero values | All | ℹ️ Tolerated | Legitimate reported zeros; filtered in revenue tables (>0) |
        """)
    except Exception as e:
        st.error(f"Error: {e}")


st.sidebar.markdown("---")
st.sidebar.caption("© 2025 Financial Intelligence Platform")
st.sidebar.caption("Data: GB XBRL · EU XBRL · US EDGAR via S3/BigQuery")
