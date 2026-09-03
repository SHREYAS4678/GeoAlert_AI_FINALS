"""
GeoAlert Agentic Dashboard
Streamlit Cloud Deployment Ready
"""

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from google.cloud import bigquery
import requests
import json

# ── PAGE CONFIG ──
st.set_page_config(
    page_title="GeoAlert — Agentic AI",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ──
st.markdown("""
<style>
    .main { background-color: #0a0e14; }
    .stApp { background: linear-gradient(135deg, #0d1b2a 0%, #1b2838 100%); }
    .risk-critical { color: #c75c5c; font-weight: bold; font-size: 24px; }
    .risk-high { color: #d4864a; font-weight: bold; font-size: 24px; }
    .risk-medium { color: #d4a03c; font-weight: bold; font-size: 24px; }
    .risk-low { color: #4caf7d; font-weight: bold; font-size: 24px; }
    .metric-card { 
        background: #111820; 
        border: 1px solid #2a3544; 
        border-radius: 8px; 
        padding: 16px; 
    }
    .agent-card {
        background: #1a2230;
        border-left: 3px solid #4f86c6;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# ── FIREBASE INIT ──
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            # Streamlit Cloud: use secrets
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": st.secrets["firebase"]["project_id"],
                "private_key": st.secrets["firebase"]["private_key"],
                "client_email": st.secrets["firebase"]["client_email"],
            })
            firebase_admin.initialize_app(cred)
        except Exception:
            # Local dev: use file
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ── SIDEBAR ──
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/111820/4f86c6?text=GEOALERT", use_column_width=True)
    st.title("Navigation")
    
    page = st.radio("", [
        "📊 Live Dashboard",
        "🗺️ Node Map",
        "🤖 Agent Control",
        "⚠️ Alert History",
        "🔋 Power Monitor",
        "💬 AI Chat",
    ])
    
    st.divider()
    st.caption("GeoAlert v5.0")
    st.caption("Agentic AI Landslide Monitoring")

# ── DATA FETCHERS ──
@st.cache_data(ttl=30)
def get_latest_readings(node_id="GA-001", limit=100):
    docs = db.collection("sensor_readings")\
        .where("node_id", "==", node_id)\
        .order_by("timestamp", direction=firestore.Query.DESCENDING)\
        .limit(limit).stream()
    return [d.to_dict() for d in docs]

@st.cache_data(ttl=60)
def get_all_nodes():
    docs = db.collection("nodes").stream()
    return [d.to_dict() for d in docs]

@st.cache_data(ttl=10)
def get_recent_alerts(limit=20):
    docs = db.collection("alerts")\
        .order_by("timestamp", direction=firestore.Query.DESCENDING)\
        .limit(limit).stream()
    return [d.to_dict() for d in docs]

# ── PAGE: LIVE DASHBOARD ──
if page == "📊 Live Dashboard":
    st.title("GeoAlert — Live Sensor Dashboard")
    
    # Node selector
    nodes = get_all_nodes()
    node_options = [n["node_id"] for n in nodes] if nodes else ["GA-001"]
    selected_node = st.selectbox("Select Monitoring Node", node_options)
    
    # Fetch data
    data = get_latest_readings(selected_node, 200)
    if not data:
        st.warning("No data received yet. Check ESP32 connection.")
        st.stop()
    
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    # ── RISK GAUGE ──
    latest = df.iloc[-1]
    risk_score = latest.get('risk_score', 0) or 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        if risk_score >= 85:
            st.markdown(f'<p class="risk-critical">🔴 CRITICAL<br>{risk_score:.0f}/100</p>', unsafe_allow_html=True)
        elif risk_score >= 70:
            st.markdown(f'<p class="risk-high">🟠 HIGH<br>{risk_score:.0f}/100</p>', unsafe_allow_html=True)
        elif risk_score >= 50:
            st.markdown(f'<p class="risk-medium">🟡 MEDIUM<br>{risk_score:.0f}/100</p>', unsafe_allow_html=True)
        else:
            st.markdown(f'<p class="risk-low">🟢 LOW<br>{risk_score:.0f}/100</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Soil Moisture", f"{latest.get('soil', 0):.2f}V", 
                  delta=f"{latest.get('soil', 0) - df.iloc[-10].get('soil', 0):.2f}V")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Rainfall", f"{latest.get('rain', 0):.0f}", 
                  delta=f"{latest.get('rain', 0) - df.iloc[-10].get('rain', 0):.0f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Temperature", f"{latest.get('temp', 0):.1f}°C")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col5:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Battery", f"{latest.get('batt', 0):.2f}V", 
                  delta=None if latest.get('batt', 4) > 3.3 else "⚠️ Low")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ── TIME SERIES CHARTS ──
    st.subheader("Sensor Trends (Last 6 Hours)")
    
    tab1, tab2, tab3 = st.tabs(["Soil & Rain", "Motion & Tilt", "Risk Score"])
    
    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['soil'], name="Soil Moisture", 
                                 line=dict(color='#4f86c6')))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['rain']/200, name="Rainfall (÷200)", 
                                 line=dict(color='#4caf7d')))
        fig.update_layout(template='plotly_dark', height=350, 
                         paper_bgcolor='#111820', plot_bgcolor='#0a0e14')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df.get('vib', 0), name="Vibration Events", 
                                 line=dict(color='#d4a03c')))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df.get('ax', 0), name="Tilt X", 
                                 line=dict(color='#9b6bc7')))
        fig.update_layout(template='plotly_dark', height=350,
                         paper_bgcolor='#111820', plot_bgcolor='#0a0e14')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        fig = go.Figure()
        colors = ['#4caf7d' if r < 50 else '#d4a03c' if r < 70 else '#d4864a' if r < 85 else '#c75c5c' 
                  for r in df.get('risk_score', [0]*len(df))]
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df.get('risk_score', 0), 
                                 name="Risk Score", mode='lines+markers',
                                 marker=dict(color=colors, size=6),
                                 line=dict(color='#4f86c6', width=2)))
        fig.add_hline(y=85, line_dash="dash", line_color="#c75c5c", annotation_text="CRITICAL")
        fig.add_hline(y=70, line_dash="dash", line_color="#d4864a", annotation_text="HIGH")
        fig.update_layout(template='plotly_dark', height=350,
                         paper_bgcolor='#111820', plot_bgcolor='#0a0e14')
        st.plotly_chart(fig, use_container_width=True)
    
    # ── RAW DATA TABLE ──
    with st.expander("View Raw Data"):
        st.dataframe(df.tail(20), use_container_width=True)

# ── PAGE: NODE MAP ──
elif page == "🗺️ Node Map":
    st.title("Monitoring Network")
    
    nodes = get_all_nodes()
    if not nodes:
        st.warning("No nodes registered.")
        st.stop()
    
    map_data = pd.DataFrame([
        {"lat": n.get("lat", 28.2), "lon": n.get("lon", 83.9), 
         "node": n["node_id"], "status": n.get("status", "UNKNOWN"),
         "battery": n.get("battery_voltage", 0)}
        for n in nodes
    ])
    
    st.map(map_data, latitude="lat", longitude="lon", size=100, color="#4f86c6")
    
    st.subheader("Node Status")
    for node in nodes:
        cols = st.columns([2, 2, 2, 2, 1])
        cols[0].write(f"**{node['node_id']}**")
        cols[1].write(node.get("status", "—"))
        cols[2].write(f"🔋 {node.get('battery_voltage', 0):.2f}V")
        cols[3].write(f"📶 {node.get('gsm_signal', 0)}")
        if node.get("status") == "DEGRADED":
            cols[4].error("⚠️")

# ── PAGE: AGENT CONTROL ──
elif page == "🤖 Agent Control":
    st.title("Agentic AI Control Panel")
    
    agents = {
        "SenseAgent": {"status": "🟢 ACTIVE", "color": "#4f86c6", 
                      "actions": ["Recalibrate Sensors", "Switch WiFi↔GSM", "Force Reading"]},
        "PredictAgent": {"status": "🟢 ACTIVE", "color": "#4caf7d",
                        "actions": ["Run Inference", "Check Drift", "Trigger Retrain"]},
        "AlertAgent": {"status": "🟢 ACTIVE", "color": "#c75c5c",
                      "actions": ["Test SMS", "Test Voice", "View Escalation Log"]},
        "PowerAgent": {"status": "🟢 ACTIVE", "color": "#d4864a",
                      "actions": ["Send Sleep Command", "Check Solar Forecast", "Blackout Prediction"]},
        "DeployAgent": {"status": "🟢 ACTIVE", "color": "#9b6bc7",
                       "actions": ["Run Health Check", "OTA Update", "Rollback"]},
    }
    
    for name, info in agents.items():
        with st.container():
            st.markdown(f"""
            <div class="agent-card" style="border-left-color: {info['color']}">
                <h4>{name} <span style="color: {info['color']}">{info['status']}</span></h4>
            </div>
            """, unsafe_allow_html=True)
            
            cols = st.columns(len(info["actions"]))
            for i, action in enumerate(info["actions"]):
                if cols[i].button(action, key=f"{name}_{action}"):
                    st.toast(f"{name}: {action} triggered!", icon="🚀")

# ── PAGE: ALERT HISTORY ──
elif page == "⚠️ Alert History":
    st.title("Alert Log")
    
    alerts = get_recent_alerts(50)
    if not alerts:
        st.info("No alerts in recent history.")
        st.stop()
    
    for alert in alerts:
        risk = alert.get("risk_score", 0)
        if risk >= 85: emoji, color = "🔴", "#c75c5c"
        elif risk >= 70: emoji, color = "🟠", "#d4864a"
        elif risk >= 50: emoji, color = "🟡", "#d4a03c"
        else: emoji, color = "🟢", "#4caf7d"
        
        with st.container():
            st.markdown(f"""
            <div style="background: #111820; border-left: 3px solid {color}; 
                        border-radius: 6px; padding: 12px; margin: 8px 0;">
                <b>{emoji} {alert.get('node_id', 'Unknown')}</b> — 
                Risk: <b style="color: {color}">{risk:.0f}/100</b><br>
                <small>{alert.get('timestamp', '—')} | 
                {alert.get('primary_driver', 'Unknown driver')}</small>
            </div>
            """, unsafe_allow_html=True)

# ── PAGE: POWER MONITOR ──
elif page == "🔋 Power Monitor":
    st.title("Energy & Solar Forecast")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Battery Status")
        # Mock data — replace with real Firestore query
        battery_data = pd.DataFrame({
            "time": pd.date_range(end=datetime.now(), periods=24, freq="H"),
            "voltage": 3.7 + np.random.randn(24) * 0.1,
            "soc": 70 + np.cumsum(np.random.randn(24) * 2),
        })
        battery_data["soc"] = battery_data["soc"].clip(0, 100)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=battery_data["time"], y=battery_data["soc"],
                                 fill='tozeroy', name="State of Charge %",
                                 line=dict(color='#4caf7d')))
        fig.update_layout(template='plotly_dark', height=300,
                         paper_bgcolor='#111820', plot_bgcolor='#0a0e14')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Solar Yield Forecast")
        forecast = pd.DataFrame({
            "hour": range(24),
            "yield": [0, 0, 0, 0, 0.1, 0.5, 1.2, 2.1, 2.8, 3.0, 2.9, 2.5,
                     2.0, 1.8, 1.5, 1.2, 0.8, 0.4, 0.1, 0, 0, 0, 0, 0]
        })
        fig = px.bar(forecast, x="hour", y="yield", color="yield",
                     color_continuous_scale=["#1a2230", "#d4a03c"])
        fig.update_layout(template='plotly_dark', height=300,
                         paper_bgcolor='#111820', plot_bgcolor='#0a0e14')
        st.plotly_chart(fig, use_container_width=True)
    
    st.info("💡 PowerAgent recommends: **Normal sleep cycle (60s)** — solar yield sufficient for next 24h.")

# ── PAGE: AI CHAT ──
elif page == "💬 AI Chat":
    st.title("GeoAlert AI Assistant")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "I am GeoAlert AI. Ask me about any sensor reading, alert, or landslide risk."
        }]
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about risk, sensors, or alerts..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response using Gemini API
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                try:
                    # Use Gemini if API key available
                    gemini_key = st.secrets.get("gemini", {}).get("api_key", "")
                    if gemini_key:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={gemini_key}"
                        body = {
                            "contents": [{
                                "parts": [{
                                    "text": f"You are GeoAlert AI, a landslide monitoring expert. Answer concisely: {prompt}"
                                }]
                            }]
                        }
                        resp = requests.post(url, json=body, timeout=15)
                        answer = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        answer = "Gemini API key not configured. Add it to Streamlit secrets to enable AI chat."
                except Exception as e:
                    answer = f"AI service temporarily unavailable. Error: {str(e)[:100]}"
            
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
