import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Pearson AI Control Tower", layout="wide")
st.title("🛫 AI Control Panel for Runway Scheduling & Weather Delays")

# Sidebar Inputs
st.sidebar.header("Simulation Settings")

# Scenario dropdown
performance = st.sidebar.selectbox("Performance Scenario", ["Bad", "Medium", "Good", "Excellent"])
weather = st.sidebar.selectbox("Weather Condition", ["Clear ☀️", "Light Rain 🌧️", "Thunderstorm ⛈️", "Fog 🌫️"])
num_flights = st.sidebar.slider("Number of Flights", 10, 50, 20)

# Delay probability and duration factor mappings
delay_probs = {
    "Bad": 0.5,
    "Medium": 0.3,
    "Good": 0.2,
    "Excellent": 0.0
}

weather_factors = {
    "Clear ☀️": 0.0,
    "Light Rain 🌧️": 0.2,
    "Thunderstorm ⛈️": 0.4,
    "Fog 🌫️": 0.3
}

# Create flight data
np.random.seed(1)
flights = pd.DataFrame({
    "Flight ID": [f"F{1000 + i}" for i in range(num_flights)],
    "Type": np.random.choice(["Arrival", "Departure"], size=num_flights),
    "Scheduled Time": np.sort(np.random.randint(0, 120, num_flights))
})

# Apply delays before AI
delay_chance = delay_probs[performance]
weather_impact = weather_factors[weather]

flights["Delayed"] = np.random.rand(num_flights) < delay_chance
flights["Delay (min)"] = flights["Delayed"] * (np.random.randint(5, 30, num_flights) * (1 + weather_impact)).round()
flights["New Time"] = flights["Scheduled Time"] + flights["Delay (min)"]

# Display results
st.subheader("📋 Simulated Flight Schedule (Before AI Optimization)")
st.dataframe(flights)

st.markdown("---")
st.info(f"Scenario: **{performance}** | Weather: **{weather}** | Delay chance: {int(delay_chance * 100)}% | Weather impact factor: {weather_impact}")
