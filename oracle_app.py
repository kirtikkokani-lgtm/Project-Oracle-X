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

# --- ANGEL ONE LOGIN LOGIC (Persistent) ---
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

# --- AI & TECHNICAL LOGIC ---
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

# --- UI HEADER ---
st.title("🔮 Oracle-X v3.4: Stable AI Terminal")

# --- SESSION STATE MANAGEMENT ---
if "smart_api" not in st.session_state:
    st.session_state.smart_api = None
if "login_success" not in st.session_state:
    st.session_state.login_success = False

# --- SIDEBAR LOGIN ---
st.sidebar.header("🔐 Angel One Secure Login")
totp_input = st.sidebar.text_input("Enter TOTP QR Key", type="password")
pin_input = st.sidebar.text_input("Enter 4-Digit PIN", type="password")

if st.sidebar.button("Connect Account"):
    with st.sidebar.spinner("Connecting..."):
        res = angel_login(totp_input, pin_input)
        if res:
            st.session_state.smart_api = res
            st.session_state.login_success = True
            st.sidebar.success("Account Connected! ✅")
        else:
            st.session_state.login_success = False
            st.sidebar.error("Login Failed. Check Credentials.")

# --- MAIN INTERFACE ---
ticker = st.text_input("Symbol (NSE)", value="RELIANCE.NS")

col1, col2 = st.columns([2, 1])

with col1:
    # स्कॅन बटण दाबल्यावर लॉगिन टिकवून ठेवण्यासाठी आपण session_state चेक करू
    if st.button("🔍 Run AI Deep Scan"):
        with st.spinner(f"Scanning {ticker}..."):
            data_feed = yf.Ticker(ticker)
            df = data_feed.history(period="1mo", interval="1h")
            
            if not df.empty:
                price = float(df['Close'].iloc[-1])
                rsi = float(get_rsi(df['Close']).iloc[-1])
                target = predict_price(df['Close'])
                
                # Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Price", f"₹{price:.2f}")
                m2.metric("Target", f"₹{target:.2f}", f"{target-price:+.2f}")
                m3.metric("RSI", f"{rsi:.1f}")
                
                # Chart
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.add_hline(y=target, line_dash="dot", line_color="cyan")
                fig.update_layout(template="plotly_dark", height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # DB
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO signals VALUES (?,?,?,?,?,?)", 
                             (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ticker, price, rsi, "SCAN", target))
                conn.commit()
                conn.close()
            else:
                st.error("Data Not Found. Try 'SBIN.NS'")

with col2:
    st.subheader("💼 Live Portfolio & Trade")
    # इथे आपण st.session_state.login_success वापरत आहोत
    if st.session_state.login_success and st.session_state.smart_api:
        try:
            profile_data = st.session_state.smart_api.rmsLimit()
            if profile_data['status']:
                cash = profile_data['data']['availablecash']
                st.info(f"💰 **Margin:** ₹{cash}")
                
                user_info = st.session_state.smart_api.getProfile()
                st.write(f"👤 **User:** {user_info['data']['name']}")
                
                st.divider()
                qty = st.number_input("Quantity", min_value=1, step=1, key="order_qty_new")
                if st.button("🚀 EXECUTE BUY", type="primary"):
                    st.success(f"Order for {qty} shares of {ticker} initiated!")
            else:
                st.session_state.login_success = False
                st.warning("Session Timeout. Please Reconnect.")
        except:
            st.session_state.login_success = False
            st.error("Session Expired. Please login again.")
    else:
        st.warning("👈 Sidebar मधून लॉगिन करा.")

# --- HISTORY ---
if st.checkbox("Show Scans"):
    conn = sqlite3.connect(DB_NAME)
    hist_df = pd.read_sql_query("SELECT * FROM signals ORDER BY timestamp DESC LIMIT 5", conn)
    st.dataframe(hist_df, use_container_width=True)
    conn.close()
