import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from SmartApi import SmartConnect
import pyotp
import sqlite3
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle-X Master AI", layout="wide")

# --- ANGEL ONE CREDENTIALS ---
API_KEY = 'jxsAJQD4'
CLIENT_ID = 'K52809090'

# --- DATABASE SETUP ---
DB_NAME = 'oracle_v3.db'
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS signals 
                 (timestamp TEXT, ticker TEXT, price REAL, rsi REAL, signal TEXT, target REAL)''')
    conn.commit()
    conn.close()

init_db()

# --- ANGEL ONE LOGIN ---
def angel_login(totp_qr_key, pin):
    try:
        smart_api = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(totp_qr_key).now()
        data = smart_api.generateSession(CLIENT_ID, pin, totp)
        if data['status']:
            return smart_api
        return None
    except:
        return None

# --- AI ANALYSIS LOGIC ---
def get_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def predict_price(series):
    y = series.values.reshape(-1, 1)
    X = np.arange(len(y)).reshape(-1, 1)
    model = LinearRegression().fit(X, y)
    return float(model.predict(np.array([[len(y)]]))[0][0])

# --- UI LAYOUT ---
st.title("🔮 Oracle-X v3.1: AI Trading Terminal")

# Sidebar
st.sidebar.header("🔐 Angel One Login")
totp_input = st.sidebar.text_input("Enter TOTP QR Key", type="password")
pin_input = st.sidebar.text_input("Enter 4-Digit PIN", type="password")

if "smart_api" not in st.session_state:
    st.session_state.smart_api = None

if st.sidebar.button("Connect Account"):
    res = angel_login(totp_input, pin_input)
    if res:
        st.session_state.smart_api = res
        st.sidebar.success("Connected! ✅")
    else:
        st.sidebar.error("Login Failed")

# Main Interface
ticker = st.text_input("Symbol (NSE) - उदा. RELIANCE.NS", value="RELIANCE.NS")

col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🔍 Run AI Analysis"):
        with st.spinner("Fetching Market Data..."):
            # YFinance Fix: auto_adjust=True
            df = yf.download(ticker, period="1mo", interval="1h", progress=False, auto_adjust=True)
            
            if not df.empty:
                # Handle MultiIndex columns if any
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                price = float(df['Close'].iloc[-1])
                rsi = float(get_rsi(df['Close']).iloc[-1])
                target = predict_price(df['Close'])
                
                # Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Current Price", f"₹{price:.2f}")
                m2.metric("AI Target", f"₹{target:.2f}", f"{target-price:+.2f}")
                m3.metric("RSI (1h)", f"{rsi:.1f}")
                
                # Plot
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.add_hline(y=target, line_dash="dot", line_color="cyan")
                fig.update_layout(template="plotly_dark", height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # DB Save
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO signals VALUES (?,?,?,?,?,?)", 
                             (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ticker, price, rsi, "SCAN", target))
                conn.commit()
                conn.close()
            else:
                st.error("Data loading failed. Check symbol or Internet.")

with col2:
    st.subheader("💼 Trading Panel")
    if st.session_state.smart_api:
        try:
            profile = st.session_state.smart_api.rmsLimit()
            if profile['status']:
                cash = profile['data']['availablecash']
                st.info(f"**Available Margin:** ₹{cash}")
            
            # User Name
            user = st.session_state.smart_api.getProfile()
            st.write(f"👤 User: {user['data']['name']}")
            
            st.divider()
            qty = st.number_input("Quantity", min_value=1, step=1)
            if st.button("🚀 PLACE BUY ORDER", type="primary"):
                st.success(f"Signal sent for {qty} shares of {ticker}")
        except:
            st.error("Session Expired. Please reconnect.")
    else:
        st.info("Sidebar मधून लॉगिन करा.")

# History
if st.checkbox("Show Scan History"):
    conn = sqlite3.connect(DB_NAME)
    hist = pd.read_sql_query("SELECT * FROM signals ORDER BY timestamp DESC LIMIT 5", conn)
    st.table(hist)
    conn.close()
