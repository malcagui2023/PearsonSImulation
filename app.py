import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import base64
import time
from io import BytesIO
import datetime

# ==========================================================
# Page Configuration (must be first Streamlit command)
# ==========================================================
st.set_page_config(page_title="Value Investing Checklist", layout="wide")

# ==========================================================
# Chart Theme: Dark Theme via Matplotlib
# ==========================================================
plt.style.use("dark_background")
plt.rcParams.update({
    "axes.facecolor": "#1e1e1e",
    "figure.facecolor": "#1e1e1e",
    "axes.edgecolor": "#444444",
    "axes.labelcolor": "white",
    "xtick.color": "white",
    "ytick.color": "white",
    "text.color": "white",
    "grid.color": "#444444",
    "grid.linestyle": "--",
    "legend.edgecolor": "white"
})

# ==========================================================
# Top Section: Logo + Title + Byline
# ==========================================================
def load_logo_base64(logo_path: str) -> str:
    with open(logo_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_data = load_logo_base64("SCM-Analytics Logo.jfif")
top_html = f"""
<div style="display:flex; align-items:center; margin-bottom:0.5rem;">
    <a href="https://scm-analytics.com/" target="_blank">
        <img src="data:image/jpg;base64,{logo_data}" style="width:80px; margin-right:15px;" alt="SCM Analytics Logo"/>
    </a>
    <div>
        <h1 style="margin:0; font-size:2rem;">Value Investing Checklist (Year-by-Year)</h1>
        <p style="margin:0; font-size:1rem; color:lightgray;">By Manuel A. Casas</p>
    </div>
</div>
"""
st.markdown(top_html, unsafe_allow_html=True)

# ==========================================================
# Input: Ticker Symbol
# ==========================================================
ticker = st.text_input("Enter Ticker Symbol (e.g., AAPL, NVDA, RY.TO)", value="AAPL")

# ==========================================================
# Data Loading with Retry/Backoff + Utility Functions
# ==========================================================
@st.cache_data(ttl=3600)
def get_data(ticker):
    """
    Fetch financials, balance sheet, history, and dividends.
    Retries up to 5 times on rate-limit errors with exponential backoff.
    """
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            bs   = stock.balance_sheet  or pd.DataFrame()
            fin  = stock.financials     or pd.DataFrame()
            hist = stock.history(period="10y")
            div  = stock.dividends      or pd.Series(dtype="float64")
            return info, bs, fin, hist, div

        except Exception as e:
            msg = str(e)
            if "Too Many Requests" in msg or "rate limit" in msg.lower():
                wait = 2 ** attempt
                st.warning(f"Rate limited by Yahoo Finance. Retrying in {wait}s…")
                time.sleep(wait)
                continue
            raise

    st.error("❗ Still rate limited after several retries—please wait a minute and try again.")
    return {}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.Series(dtype="float64")

def safe_ratio(numerator, denominator):
    try:
        return numerator / denominator if denominator and denominator != 0 else None
    except:
        return None

def get_recent_years(df, max_years=10):
    if df.empty:
        return []
    try:
        years = sorted({col.year for col in df.columns})
    except Exception:
        years = sorted({idx.year for idx in df.index})
    return years[-max_years:]

# ==========================================================
# Main Processing Block
# ==========================================================
if ticker:
    try:
        info, bs, fin, hist, div = get_data(ticker)
        fiscal_years = get_recent_years(fin, 10)
        if len(fiscal_years) < 10:
            fiscal_years = get_recent_years(fin, 5)

        # ----------------------------
        # Price Chart (Top Section)
        # ----------------------------
        st.subheader("📈 Stock Price (Last 10 Years)")
        fig_price, ax_price = plt.subplots(figsize=(10, 3))
        hist["Close"].resample("ME").last().plot(ax=ax_price, color="orange")
        ax_price.set_title(f"{ticker} Monthly Closing Prices")
        ax_price.set_xlabel("Date")
        ax_price.set_ylabel("Price (USD)")
        ax_price.grid(True)
        st.pyplot(fig_price)

        # ----------------------------
        # Evaluate Metrics & Build Summary
        # ----------------------------
        summary = []
        metric_data = {}

        def evaluate_metric(name, vals, threshold=None, comp=">", is_pct=True):
            fails = 0
            data = {}
            for y in fiscal_years:
                v = vals.get(y)
                if v is None:
                    data[y] = "Missing"
                else:
                    pv = v * 100 if is_pct else v
                    data[y] = round(pv, 2)
                    if threshold is not None:
                        if comp == ">" and pv < threshold*100:
                            fails += 1
                        elif comp == "<" and pv > threshold*100:
                            fails += 1
            metric_data[name] = data
            pf = "✅" if fails == 0 else "❌"
            summary.append((name, pf, f"{len(fiscal_years)-fails} / {len(fiscal_years)} years passed"))

        # ---- ROE ≥12% ----
        roe = {}
        for y in fiscal_years:
            try:
                net = fin.loc["Net Income", fin.columns[fin.columns.year==y]].values[0]
                eq  = bs.loc["Total Stockholder Equity", bs.columns[bs.columns.year==y]].values[0]
                roe[y] = safe_ratio(net, eq)
            except:
                roe[y] = None
        evaluate_metric("ROE ≥ 12%", roe, threshold=0.12)

        # ---- ROA ≥12% ----
        roa = {}
        for y in fiscal_years:
            try:
                net = fin.loc["Net Income", fin.columns[fin.columns.year==y]].values[0]
                ast = bs.loc["Total Assets", bs.columns[bs.columns.year==y]].values[0]
                roa[y] = safe_ratio(net, ast)
            except:
                roa[y] = None
        evaluate_metric("ROA ≥ 12%", roa, threshold=0.12)

        # ---- EPS Per Share (no threshold) ----
        eps = {}
        shares = info.get("sharesOutstanding")
        for y in fiscal_years:
            try:
                net = fin.loc["Net Income", fin.columns[fin.columns.year==y]].values[0]
                eps[y] = safe_ratio(net, shares) if shares else None
            except:
                eps[y] = None
        metric_data["EPS Per Share"] = {y:(round(v*100,2) if v is not None else "Missing") for y,v in eps.items()}
        avail = sum(1 for v in eps.values() if v is not None)
        summary.append(("EPS Per Share", "—", f"{avail} / {len(fiscal_years)} yrs avail"))

        # ---- Net Margin ≥20% ----
        nm = {}
        for y in fiscal_years:
            try:
                net = fin.loc["Net Income", fin.columns[fin.columns.year==y]].values[0]
                rev = fin.loc["Total Revenue", fin.columns[fin.columns.year==y]].values[0]
                nm[y] = safe_ratio(net, rev)
            except:
                nm[y] = None
        evaluate_metric("Net Margin ≥ 20%", nm, threshold=0.20)

        # ---- Gross Margin ≥40% ----
        gm = {}
        for y in fiscal_years:
            try:
                gp  = fin.loc["Gross Profit", fin.columns[fin.columns.year==y]].values[0]
                rev = fin.loc["Total Revenue", fin.columns[fin.columns.year==y]].values[0]
                gm[y] = safe_ratio(gp, rev)
            except:
                gm[y] = None
        evaluate_metric("Gross Margin ≥ 40%", gm, threshold=0.40)

        # ---- RORC ≥18% ----
        rorc = {}
        for y in fiscal_years:
            try:
                net  = fin.loc["Net Income", fin.columns[fin.columns.year==y]].values[0]
                d    = div[div.index.year==y].sum()
                rorc[y] = safe_ratio(net, net - d)
            except:
                rorc[y] = None
        evaluate_metric("Return on Retained Capital ≥ 18%", rorc, threshold=0.18)

        # ---- LT Debt ÷ Net Income <5x ----
        try:
            ly   = fiscal_years[-1]
            debt = bs.loc["Long Term Debt", bs.columns[bs.columns.year==ly]].values[0]
            netl = fin.loc["Net Income", fin.columns[fin.columns.year==ly]].values[0]
            lr   = safe_ratio(debt, netl)
            lc   = f"{lr:.2f}x" if lr is not None else "Missing"
            summary.append(("LT Debt ÷ Net Income < 5x", "✅" if lr is not None and lr<5 else "❌", lc))
        except:
            summary.append(("LT Debt ÷ Net Income < 5x", "⚠️", "Missing"))

        # ---- Pricing Power vs. Inflation (commentary) ----
        cpi = 0.032
        pc  = f"Compare price moves vs US CPI of ~{cpi*100:.1f}%. [Source: BLS] (EXAMPLE – Research on Your Own)"
        summary.append(("Pricing Power vs. Inflation", "—", pc))

        # ---- Organized Labor (commentary) ----
        lcmt = "Review 10-K & news for union or strike risk. [Example: Reuters 2023] (EXAMPLE – Research on Your Own)"
        summary.append(("Organized Labor", "—", lcmt))

        # ---- Dividends & Buybacks (commentary) ----
        yrs = sorted(set(div.index.year)) if not div.empty else []
        if not yrs:
            d_c = "No Dividends or Buybacks"
            ds  = "—
