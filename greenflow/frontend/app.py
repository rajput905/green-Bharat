import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# 1. Page Configuration
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GreenFlow AI Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling - Glassmorphism & Neon accents
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Inter:wght@300;400;600&display=swap');
    
    .main {
        background: radial-gradient(circle at 50% 50%, #1a1c2c 0%, #0e1117 100%);
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    .stMetric {
        background: rgba(30, 33, 48, 0.6);
        backdrop-filter: blur(10px);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(0, 212, 255, 0.2);
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    h1, h2, h3 {
        font-family: 'Orbitron', sans-serif;
        letter-spacing: 2px;
        color: #00d4ff !important;
        text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
    }
    .stAlert {
        background: rgba(255, 75, 75, 0.1) !important;
        border: 1px solid rgba(255, 75, 75, 0.3) !important;
        color: #ff4b4b !important;
    }
    div[data-testid="stSidebar"] {
        background-color: #0e1117;
        border-right: 1px solid rgba(0, 212, 255, 0.1);
    }
    .chart-container {
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 10px;
        background: rgba(255, 255, 255, 0.02);
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 2. State & Constants
# ─────────────────────────────────────────────────────────────────────────────
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Auto-refresh every 5 seconds
st_autorefresh(interval=5000, key="datarefresh")

class ChatResponse(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    data_points: dict = Field(default_factory=dict, description="Additional data points related to the answer, e.g., sources, latency.")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Helper Functions
# ─────────────────────────────────────────────────────────────────────────────
def get_api_data(endpoint: str):
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}", timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception:
        return None
    return None

def send_chat_query(query: str):
    try:
        response = requests.post(
            f"{API_BASE_URL}/chatbot/",
            json={"query": query},
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return {"answer": f"Agent Synchronization Offline: {str(e)}"}
    return {"answer": "Error communicating with AI command intelligence."}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Header & Sidebar
# ─────────────────────────────────────────────────────────────────────────────
st.title("🌿 GREENFLOW AI: COMMAND CENTER")

with st.sidebar:
    st.markdown("### 🛰️ GLOBAL STATUS")
    alerts = get_api_data("analytics/alerts")
    if alerts:
        for alert in alerts:
            st.warning(f"**{alert['severity']}**: {alert['alert_message']}")
    else:
        st.success("STABLE – NO ANOMALIES")
    
    st.divider()
    st.markdown("### ⚙️ SYSTEM")
    st.write(f"**SYNC:** {datetime.now().strftime('%H:%M:%S')}")
    st.progress(85, text="PIPELINE LOAD")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Main Dashboard Metrics
# ─────────────────────────────────────────────────────────────────────────────
risk_data = get_api_data("analytics/risk-score")
live_data = get_api_data("analytics/live-data?limit=50")

m1, m2, m3, m4 = st.columns(4)

if risk_data:
    m1.metric("RISK INDEX", f"{risk_data['current_score']}", delta_color="inverse")
    color = "🔴" if risk_data['safety_level'] == "CRITICAL" else "🟢"
    m2.metric("SAFETY PROTOCOL", f"{color} {risk_data['safety_level']}")
else:
    m1.metric("RISK INDEX", "OFFLINE")
    m2.metric("SAFETY PROTOCOL", "INIT...")

if live_data and len(live_data) > 0:
    latest = live_data[0]
    m3.metric("AQI LIVE", f"{latest['aqi']}", f"{latest.get('avg_aqi_10m', 0):.1f} avg")
    m4.metric("CONGESTION", f"{latest.get('congestion_pct', 'N/A')}%")
else:
    m3.metric("AQI LIVE", "---")
    m4.metric("CONGESTION", "---")

# ─────────────────────────────────────────────────────────────────────────────
# 6. Digital Twin & Analytics Map
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
c1, c2 = st.columns([2, 1])

with c1:
    st.markdown("### 🗺️ DIGITAL TWIN: SENSOR TOPOLOGY")
    # Simulated Map for Visual Wow
    map_data = pd.DataFrame({
        'lat': [28.6139, 28.6180, 28.6100, 28.6200],
        'lon': [77.2090, 77.2150, 77.2000, 77.2200],
        'status': ['Stable', 'Stable', 'Warning', 'Stable']
    })
    fig_map = go.Figure(go.Scattermapbox(
        lat=map_data['lat'], lon=map_data['lon'],
        mode='markers',
        marker=go.scattermapbox.Marker(size=14, color='cyan', opacity=0.7),
        text=map_data['status'],
    ))
    fig_map.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox={"center": {"lat": 28.6139, "lon": 77.2090}, "zoom": 12},
        margin={"r":0,"t":0,"l":0,"b":0},
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig_map, use_container_width=True, key="map_viz")

with c2:
    st.markdown("### 📈 ANALYTICS")
    if live_data:
        df = pd.DataFrame(live_data)
        df['time'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.sort_values('time')
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=df['time'], y=df['aqi'], name="AQI", line={"color": "#00d4ff", "width": 2}))
        fig_trend.update_layout(
            template="plotly_dark",
            height=400,
            margin={"l":0,"r":0,"t":0,"b":0},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False
        )
        st.plotly_chart(fig_trend, use_container_width=True, key="trend_viz")
    else:
        st.info("Awaiting pipeline stream...")

# ─────────────────────────────────────────────────────────────────────────────
# 7. AI Chat Interface
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.subheader("🤖 AI Data Concierge")

chat_container = st.container(height=300)
for message in st.session_state.chat_history:
    with chat_container.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about current pollution or safety..."):
    with chat_container.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with chat_container.chat_message("assistant"):
        with st.spinner("AI is analyzing live streams..."):
            response = send_chat_query(prompt)
            st.markdown(response["answer"])
            st.session_state.chat_history.append({"role": "assistant", "content": response["answer"]})
