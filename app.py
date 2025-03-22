import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Pearson AI Control Tower", layout="wide")
st.title("🛫 AI Control Panel for Runway Scheduling & Weather Delays")

# Sidebar Inputs
st.sidebar.header("Simulation Settings")

# Scenario dropdowns
performance = st.sidebar.selectbox(
    "Performance Scenario",
    ["Bad (50% delays)", "Medium (30% delays)", "Good (20% delays)", "Excellent (0% delays)"]
)
weather = st.sidebar.selectbox(
    "Weather Condition",
    ["Clear ☀️", "Light Rain 🌧️", "Thunderstorm ⛈️", "Fog 🌫️"]
)
num_flights = st.sidebar.slider("Number of Flights", 10, 50, 20)

# Delay probability and duration factor mappings
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

# Generate flights
np.random.seed(1)
flights = pd.DataFrame({
    "Flight ID": [f"F{1000 + i}" for i in range(num_flights)],
    "Type": np.random.choice(["Arrival", "Departure"], size=num_flights),
    "Scheduled Time": np.sort(np.random.randint(0, 120, num_flights))
})

# Calculate delays BEFORE optimization
delay_chance = delay_probs[performance]
weather_impact = weather_factors[weather]

flights["Delayed Before"] = np.random.rand(num_flights) < delay_chance
flights["Delay (min) Before"] = flights["Delayed Before"] * (np.random.randint(5, 30, num_flights) * (1 + weather_impact)).round()
flights["New Time Before"] = flights["Scheduled Time"] + flights["Delay (min) Before"]

# AI Optimization Simulation
def optimize_delays(row):
    if row["Delayed Before"]:
        reduction_factor = 0.5 if delay_chance > 0 else 0
        new_delay = max(row["Delay (min) Before"] * reduction_factor * (1 - weather_impact), 0)
        return round(new_delay)
    return 0

flights["Delay (min) After"] = flights.apply(optimize_delays, axis=1)
flights["New Time After"] = flights["Scheduled Time"] + flights["Delay (min) After"]
flights["Improved"] = flights["Delay (min) Before"] > flights["Delay (min) After"]

# View Toggle
view = st.radio("Select View", ["📋 Before Optimization", "🤖 After AI Optimization", "🔁 Compare Both"])

# Display Views
if view == "📋 Before Optimization":
    st.subheader("✈️ Flight Schedule (Before AI Optimization)")
    st.dataframe(flights[["Flight ID", "Type", "Scheduled Time", "Delay (min) Before", "New Time Before"]])
elif view == "🤖 After AI Optimization":
    st.subheader("🛫 Optimized Flight Schedule (After AI)")
    st.dataframe(flights[["Flight ID", "Type", "Scheduled Time", "Delay (min) After", "New Time After"]])
else:
    st.subheader("🔁 Comparison: Before vs After Optimization")
    st.dataframe(flights[[
        "Flight ID", "Type", "Scheduled Time",
        "Delay (min) Before", "New Time Before",
        "Delay (min) After", "New Time After",
        "Improved"
    ]])

# KPI Summary
st.markdown("### 📊 Delay Summary")

col1, col2, col3 = st.columns(3)

avg_before = flights["Delay (min) Before"].mean()
avg_after = flights["Delay (min) After"].mean()
improved_count = flights["Improved"].sum()
delayed_before = (flights["Delay (min) Before"] > 0).sum()
delayed_after = (flights["Delay (min) After"] > 0).sum()

col1.metric("⏱ Avg Delay Before", f"{avg_before:.1f} min")
col2.metric("✅ Avg Delay After", f"{avg_after:.1f} min", delta=f"{avg_before - avg_after:.1f}")
col3.metric("🔄 Flights Improved", f"{improved_count}/{num_flights}")

col1.metric("⚠️ Flights Delayed Before", f"{delayed_before}")
col2.metric("🟢 Flights Delayed After", f"{delayed_after}")
col3.metric("🌦️ Weather Impact", f"{int(weather_impact * 100)}%")

# Footer Info
st.markdown("---")
st.info(f"Scenario: **{performance}** | Weather: **{weather}**")
# Dynamic performance message
st.markdown("### 📣 Control Tower Feedback")

# Calculate improvement %
if avg_before > 0:
    improvement_pct = ((avg_before - avg_after) / avg_before) * 100
else:
    improvement_pct = 0

# Dynamic message based on results
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

# Display scenario info at the bottom
st.markdown("---")
st.info(f"Scenario: **{performance}** | Weather: **{weather}** | Delay Reduction: **{improvement_pct:.1f}%**")
