import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="SKYFLOW – FLIGHTFUSION", layout="wide")

# === HEADER WITH LOGO ON RIGHT ===
col1, col2 = st.columns([9, 1])
with col1:
    st.markdown("<h1 style='margin-bottom:0;'>SKYFLOW</h1>", unsafe_allow_html=True)
    st.markdown("<h5 style='margin-top:0;'>FLIGHTFUSION – Airport Operations Management System</h5>", unsafe_allow_html=True)
with col2:
    st.image("https://raw.githubusercontent.com/malcagui2023/PearsonSImulation/main/design.png", width=40)

# === Sidebar Controls ===
st.sidebar.header("Simulation Settings")

performance = st.sidebar.selectbox(
    "Performance Scenario",
    ["Bad (50% delays)", "Medium (30% delays)", "Good (20% delays)", "Excellent (0% delays)"]
)
weather = st.sidebar.selectbox(
    "Weather Condition",
    ["Clear ☀️", "Light Rain 🌧️", "Thunderstorm ⛈️", "Fog 🌫️"]
)
num_flights = st.sidebar.slider("Number of Flights", 10, 50, 20)

delay_probs = {
    "Bad (50% delays)": 0.5,
    "Medium (30% delays)": 0.3,
    "Good (20% delays)": 0.2,
    "Excellent (0% delays)": 0.0
}

weather_factors = {
    "Clear ☀️": 0.0,
    "Light Rain 🌧️": 0.2,
    "Thunderstorm ⛈️": 0.4,
    "Fog 🌫️": 0.3
}

# === Generate Flight Data with Long Delays ===
np.random.seed(1)

flights = pd.DataFrame({
    "Flight ID": [f"F{1000 + i}" for i in range(num_flights)],
    "Type": np.random.choice(["Arrival", "Departure"], size=num_flights),
    "Scheduled Time": np.sort(np.random.randint(0, 120, num_flights))
})

delay_chance = delay_probs[performance]
weather_impact = weather_factors[weather]

# Base delays
flights["Delayed Before"] = np.random.rand(num_flights) < delay_chance
flights["Delay (min) Before"] = flights["Delayed Before"] * (
    np.random.randint(5, 30, num_flights) * (1 + weather_impact)
).round()

# Inject long delays (240+ min)
long_delay_indices = np.random.choice(flights.index, size=max(1, int(0.1 * num_flights)), replace=False)
flights.loc[long_delay_indices, "Delay (min) Before"] = np.random.randint(250, 360, len(long_delay_indices))
flights["New Time Before"] = flights["Scheduled Time"] + flights["Delay (min) Before"]

# === AI Optimization: Always Improve or Hold ===
def optimize_delay(row):
    # No delay → do nothing
    if row["Delay (min) Before"] == 0:
        return 0

    # 10% of delayed flights → fully recovered
    if np.random.rand() < 0.1:
        return 0

    # Reduce based on scenario severity
    if performance.startswith("Bad"):
        factor = 0.65
    elif performance.startswith("Medium"):
        factor = 0.5
    elif performance.startswith("Good"):
        factor = 0.4
    else:  # Excellent
        factor = 0.2

    # Weather adjustment
    reduction = row["Delay (min) Before"] * factor * (1 - weather_impact)
    return round(max(row["Delay (min) Before"] - reduction, 0))

flights["Delay (min) After"] = flights.apply(optimize_delay, axis=1)
flights["New Time After"] = flights["Scheduled Time"] + flights["Delay (min) After"]

# === 📊 KPI Summary ===
flights["Delayed After"] = flights["Delay (min) After"] > 0
flights["Improved"] = flights["Delay (min) Before"] > flights["Delay (min) After"]

avg_before = flights["Delay (min) Before"].mean()
avg_after = flights["Delay (min) After"].mean()
delayed_before = flights["Delayed Before"].sum()
delayed_after = flights["Delayed After"].sum()
improved_count = flights["Improved"].sum()

# === 💰 Cost Savings: Only from >240 min → ≤240 min
planes_costly_before = flights["Delay (min) Before"] > 240
planes_below_after = flights["Delay (min) After"] <= 240
planes_saved = planes_costly_before & planes_below_after

savings_count = planes_saved.sum()
estimated_savings = int(savings_count * 24000)

# === Display Metrics ===
st.markdown("### 💰 Potential Savings")
st.metric("Estimated Cost Savings", f"${estimated_savings:,} CAD", delta=f"{savings_count} planes improved")

st.markdown("### 📊 Delay Summary")
col1, col2, col3 = st.columns(3)
col1.metric("⏱ Avg Delay Before", f"{avg_before:.1f} min")
col2.metric("✅ Avg Delay After", f"{avg_after:.1f} min", delta=f"{avg_before - avg_after:.1f}")
col3.metric("📘 Flights Improved", f"{improved_count}/{num_flights}")

col1.metric("⚠️ Flights Delayed Before", f"{delayed_before}")
col2.metric("🟢 Flights Delayed After", f"{delayed_after}")
col3.metric("🌦️ Weather Impact", f"{int(weather_impact * 100)}%")

# === 📣 Control Tower Feedback ===
st.markdown("### 📣 Control Tower Feedback")

if avg_before > 0:
    improvement_pct = ((avg_before - avg_after) / avg_before) * 100
else:
    improvement_pct = 0

if avg_before > 15:
    if improvement_pct >= 50:
        summary_msg = "🧠 Severe congestion mitigated by AI. Major delays reduced."
    elif improvement_pct > 20:
        summary_msg = "⚠️ Heavy delays. AI made moderate improvements, but challenges remain."
    else:
        summary_msg = "❗ High delays persist. Consider additional runway or schedule optimization."
elif avg_before > 5:
    if improvement_pct >= 50:
        summary_msg = "✅ System stabilized. AI effectively reduced moderate delays."
    else:
        summary_msg = "🕓 Some delay reduction achieved. Monitor runway load."
else:
    summary_msg = "🟢 Low delay scenario. AI kept performance optimal."

st.success(summary_msg)

# === 🛬 Runway Utilization Chart ===
st.markdown("### 🛬 Runway Utilization Comparison")

flights["Runway Before"] = np.random.choice(["RW1", "RW2"], size=num_flights)
rw1_count = (flights["Runway Before"] == "RW1").sum()

if rw1_count > num_flights * 0.6:
    flights["Runway After"] = np.where(
        flights["Runway Before"] == "RW1",
        np.random.choice(["RW1", "RW2"], size=num_flights, p=[0.4, 0.6]),
        "RW2"
    )
else:
    flights["Runway After"] = flights["Runway Before"]

runway_summary = pd.DataFrame({
    "Before AI": flights["Runway Before"].value_counts(),
    "After AI": flights["Runway After"].value_counts()
}).fillna(0)

fig = go.Figure(data=[
    go.Bar(name='Before AI', x=runway_summary.index, y=runway_summary["Before AI"], marker_color='indianred'),
    go.Bar(name='After AI', x=runway_summary.index, y=runway_summary["After AI"], marker_color='seagreen')
])
fig.update_layout(
    barmode='group',
    title="Runway Allocation Comparison",
    xaxis_title="Runway",
    yaxis_title="Flights Assigned",
    height=400
)

st.plotly_chart(fig, use_container_width=True)

# === 🔁 View Toggle ===
view = st.radio("Select View", ["📋 Before Optimization", "🤖 After AI Optimization", "🔁 Compare Both"])

if view == "📋 Before Optimization":
    st.subheader("✈️ Flight Schedule (Before AI Optimization)")
    st.dataframe(flights[["Flight ID", "Type", "Scheduled Time", "Delay (min) Before", "New Time Before", "Runway Before"]])

elif view == "🤖 After AI Optimization":
    st.subheader("🛫 Optimized Flight Schedule (After AI)")
    st.dataframe(flights[["Flight ID", "Type", "Scheduled Time", "Delay (min) After", "New Time After", "Runway After"]])

else:
    st.subheader("🔁 Comparison: Before vs After Optimization")
    st.dataframe(flights[[
        "Flight ID", "Type", "Scheduled Time",
        "Delay (min) Before", "New Time Before", "Runway Before",
        "Delay (min) After", "New Time After", "Runway After",
        "Improved"
    ]])
