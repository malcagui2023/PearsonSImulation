import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Pearson AI Control Panel", layout="wide")

st.title("🛫 AI Control Panel for Runway Scheduling & Weather Delays")

# Sidebar Inputs
st.sidebar.header("Simulation Settings")
num_flights = st.sidebar.slider("Incoming Flights per Hour", 5, 30, 15)
weather_severity = st.sidebar.slider("Weather Severity", 0, 100, 40)

# Generate Fake Flights
np.random.seed(42)
flights = pd.DataFrame({
    "Flight": [f"F{100+i}" for i in range(num_flights)],
    "Scheduled Time": np.sort(np.random.randint(0, 60, num_flights)),
    "Runway": np.random.choice(["RW1", "RW2"], size=num_flights),
})

# Weather Delay Function
def apply_weather_delay(df, severity):
    df = df.copy()
    delay_factor = severity / 100
    df["Delay (min)"] = (np.random.rand(len(df)) * 30 * delay_factor).round()
    df["New Time"] = df["Scheduled Time"] + df["Delay (min)"]
    return df

# AI Optimizer Simulation
def ai_optimizer(df, severity):
    df = df.copy()
    delay_factor = severity / 100
    df["Delay (min)"] = (np.random.rand(len(df)) * 10 * delay_factor).round()
    df["New Time"] = df["Scheduled Time"] + df["Delay (min)"]
    df["Runway"] = np.where(df["New Time"] % 2 == 0, "RW1", "RW2")
    return df

# Process both scenarios
before_ai = apply_weather_delay(flights, weather_severity)
after_ai = ai_optimizer(flights, weather_severity)

# Visual Comparison
st.subheader("Flight Schedule Comparison")
tab1, tab2 = st.tabs(["🟥 Before AI Optimization", "🟩 After AI Optimization"])

with tab1:
    fig1 = px.timeline(before_ai, x_start="Scheduled Time", x_end="New Time", y="Flight", color="Runway")
    fig1.update_layout(xaxis_title="Time (min)", yaxis_title="Flight", title="Delays Due to Weather")
    st.plotly_chart(fig1, use
