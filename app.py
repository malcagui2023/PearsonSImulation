import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import base64
import time
from requests.exceptions import HTTPError
from io import BytesIO
import datetime

# ==========================================================
# Page Configuration (MUST be first Streamlit command)
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
    """Fetch financials, balance sheet, history, and dividends with retry on rate-limits."""
    for attempt in range(3):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            bs = stock.balance_sheet if stock.balance_sheet is not None else pd.DataFrame()
            fin = stock.financials if stock.financials is not None else pd.DataFrame()
            hist = stock.history(period="10y")
            div = stock.dividends if stock.dividends is not None else pd.Series(dtype="float64")
            return info, bs, fin, hist, div
        except HTTPError as e:
            if "429" in str(e):
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            else:
                raise
    st.error("❗ Too many requests—please wait a minute and try again.")
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


def format_percent(value):
    if value is None:
        return "Missing"
    try:
        return f"{value*100:.1f}%"
    except:
        return str(value)


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

        # ROE ≥12%
        roe = {}
        for y in fiscal_years:
            try:
                net = fin.loc["Net Income", fin.columns[fin.columns.year==y]].values[0]
                eq = bs.loc["Total Stockholder Equity", bs.columns[bs.columns.year==y]].values[0]
                roe[y] = safe_ratio(net, eq)
            except:
                roe[y] = None
        evaluate_metric("ROE ≥ 12%", roe, threshold=0.12)

        # ROA ≥12%
        roa = {}
        for y in fiscal_years:
            try:
                net = fin.loc["Net Income", fin.columns[fin.columns.year==y]].values[0]
                ast = bs.loc["Total Assets", bs.columns[bs.columns.year==y]].values[0]
                roa[y] = safe_ratio(net, ast)
            except:
                roa[y] = None
        evaluate_metric("ROA ≥ 12%", roa, threshold=0.12)

        # EPS Per Share (no threshold)
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

        # Net Margin ≥20%
        nm = {}
        for y in fiscal_years:
            try:
                net = fin.loc["Net Income", fin.columns[fin.columns.year==y]].values[0]
                rev = fin.loc["Total Revenue", fin.columns[fin.columns.year==y]].values[0]
                nm[y] = safe_ratio(net, rev)
            except:
                nm[y] = None
        evaluate_metric("Net Margin ≥ 20%", nm, threshold=0.20)

        # Gross Margin ≥40%
        gm = {}
        for y in fiscal_years:
            try:
                gp = fin.loc["Gross Profit", fin.columns[fin.columns.year==y]].values[0]
                rev = fin.loc["Total Revenue", fin.columns[fin.columns.year==y]].values[0]
                gm[y] = safe_ratio(gp, rev)
            except:
                gm[y] = None
        evaluate_metric("Gross Margin ≥ 40%", gm, threshold=0.40)

        # RORC ≥18%
        rorc = {}
        for y in fiscal_years:
            try:
                net = fin.loc["Net Income", fin.columns[fin.columns.year==y]].values[0]
                d = div[div.index.year==y].sum()
                rorc[y] = safe_ratio(net, net - d)
            except:
                rorc[y] = None
        evaluate_metric("Return on Retained Capital ≥ 18%", rorc, threshold=0.18)

        # LT Debt ÷ Net Income <5x
        try:
            ly = fiscal_years[-1]
            debt = bs.loc["Long Term Debt", bs.columns[bs.columns.year==ly]].values[0]
            netl = fin.loc["Net Income", fin.columns[fin.columns.year==ly]].values[0]
            lr = safe_ratio(debt, netl)
            lc = f"{lr:.2f}x" if lr is not None else "Missing"
            summary.append(("LT Debt ÷ Net Income < 5x", "✅" if lr is not None and lr<5 else "❌", lc))
        except:
            summary.append(("LT Debt ÷ Net Income < 5x", "⚠️", "Missing"))

        # Pricing vs Inflation (commentary)
        cpi = 0.032
        pc = f"Compare price moves vs US CPI of ~{cpi*100:.1f}%. [Source: BLS] (EXAMPLE – Research on Your Own)"
        summary.append(("Pricing Power vs. Inflation", "—", pc))

        # Organized Labor (commentary)
        lcmt = "Review 10-K & news for union or strike risk. [Example: Reuters 2023] (EXAMPLE – Research on Your Own)"
        summary.append(("Organized Labor", "—", lcmt))

        # Dividends & Buybacks (commentary)
        yrs = sorted(set(div.index.year)) if not div.empty else []
        if not yrs:
            d_c = "No Dividends or Buybacks"
            ds = "—"
        else:
            cuts=[]
            for i in range(1,len(yrs)):
                if div[div.index.year==yrs[i]].sum() < div[div.index.year==yrs[i-1]].sum():
                    cuts.append(yrs[i])
            d_c = f"{len(yrs)} yrs; Cuts: {cuts if cuts else 'None'} (EXAMPLE – Research on Your Own)"
            ds = "✅" if not cuts else "❌"
        summary.append(("Dividends & Buybacks", ds, d_c))

        # Barriers to Entry (commentary)
        bc = (
            "- Brand lock-in [Morningstar] (EXAMPLE – Research on Your Own)\n"
            "- Patents & tech moat [SEC 10-K] (EXAMPLE – Research on Your Own)\n"
            "- Scale cost advantage [HBR] (EXAMPLE – Research on Your Own)\n"
            "- Distribution network [WSJ] (EXAMPLE – Research on Your Own)"
        )
        summary.append(("Barriers to Entry", "—", bc))

        # ----------------------------
        # TOP SECTION: Summary Table
        # ----------------------------
        st.subheader("📋 Summary Table")
        df_sum = pd.DataFrame(summary, columns=["Metric", "Pass/Fail", "Value/Details"])
        st.table(df_sum)

        # ----------------------------
        # MIDDLE SECTION: Charts & Tables
        # ----------------------------
        st.subheader("📊 Metrics (Year-by-Year Charts & Tables)")
        for name, values in metric_data.items():
            with st.expander(f"{name}", expanded=False):
                tab_c, tab_t = st.tabs(["Chart","Table"])
                dfm = pd.DataFrame.from_dict(values, orient="index", columns=["Value"])
                dfm.index = dfm.index.map(int)
                dfm["Value"] = dfm["Value"].apply(lambda x: float(x) if isinstance(x,(int,float)) else None)
                # chart
                fig,ax = plt.subplots(figsize=(8,3))
                ax.plot(dfm.index, dfm["Value"], marker="o", color="tab:blue")
                ax.set_title(name); ax.set_xlabel("Year"); ax.set_ylabel("Percentage")
                ax.set_xticks(dfm.index); ax.grid(True,linestyle="--",linewidth=0.5)
                tab_c.pyplot(fig, clear_figure=True)
                # table
                dfd = dfm.copy()
                dfd["Value"] = dfd["Value"].apply(lambda x: f"{x:.2f}%" if isinstance(x,(int,float)) else "Missing")
                tab_t.dataframe(dfd)

        # ----------------------------
        # BOTTOM SECTION: Narrative & Disclosure
        # ----------------------------
        st.subheader("🧠 Narrative Insights & Commentary")
        st.markdown("### 🏛️ Barriers to Entry")
        st.markdown(bc)
        st.markdown("### 📉 Pricing Power vs. Inflation")
        st.markdown(pc)
        st.markdown("### 🏭 Organized Labor")
        st.markdown(lcmt)
        st.markdown("### LT Debt ÷ Net Income")
        st.markdown("See Summary Table above for the latest value.")
        st.markdown("### Dividends & Buybacks")
        st.markdown("See Summary Table above for history & cuts.")
        # --------------------------------------------------
        # Export Summary CSV
        # --------------------------------------------------
        st.subheader("📥 Export Results")
        csv = df_sum.to_csv(index=False).encode("utf-8")
        st.download_button("📤 Download Summary CSV", csv, file_name=f"{ticker}_summary.csv", mime="text/csv")
        # --------------------------------------------------
        # Disclaimer
        # --------------------------------------------------
        st.markdown("---")
        st.markdown(
            "<small>Disclaimer: For informational purposes only. Data from Yahoo Finance; accuracy not guaranteed.</small>",
            unsafe_allow_html=True
        )

    except Exception as e:
        st.error(f"Error processing ticker: {e}")
