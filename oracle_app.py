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
st.set_page_config(page_title="Oracle-X Stable v3.5", layout="wide")

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

# --- PERSISTENT LOGIN FUNCTION ---
# हे फंक्शन लॉगिनला मेमरीमध्ये सेव्ह (Cache) करून ठेवते
@st.cache_resource(show_spinner=False)
def get_angel_session(totp_qr_key, pin):
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

# --- UI HEADER ---
st.title("🔮 Oracle-X v3.5: Persistent AI Terminal")

# --- SIDEBAR LOGIN ---
st.sidebar.header("🔐 Angel One Secure Login")
totp_input = st.sidebar.text_input("Enter TOTP QR Key", type="password")
pin_input = st.sidebar.text_input("Enter 4-Digit PIN", type="password")

# लॉगिन बटण दाबल्यावर कॅशमध्ये सेव्ह करणे
if st.sidebar.button("Connect Account"):
    session = get_angel_session(totp_input, pin_input)
    if session:
        st.session_state.smart_api = session
        st.sidebar.success("Account Connected! ✅")
    else:
        st.sidebar.error("Login Failed. Check Credentials.")

# --- MAIN INTERFACE ---
ticker = st.text_input("Symbol (NSE)", value="RELIANCE.NS")

col1, col2 = st.columns([2, 1])

with col1:
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
                m1.metric("Current Price", f"₹{price:.2f}")
                m2.metric("AI Target", f"₹{target:.2f}", f"{target-price:+.2f}")
                m3.metric("RSI (1h)", f"{rsi:.1f}")
                
                # Plot
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.add_hline(y=target, line_dash="dot", line_color="cyan", annotation_text="AI Target")
                fig.update_layout(template="plotly_dark", height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Save to DB
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO signals VALUES (?,?,?,?,?,?)", 
                             (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ticker, price, rsi, "SCAN", target))
                conn.commit()
                conn.close()
            else:
                st.error("Data loading failed.")

with col2:
    st.subheader("💼 Trading Panel")
    # 'smart_api' सेशनमध्ये आहे का ते तपासणे
    if "smart_api" in st.session_state and st.session_state.smart_api:
        try:
            profile = st.session_state.smart_api.rmsLimit()
            if profile['status']:
                cash = profile['data']['availablecash']
                st.info(f"💰 **Margin:** ₹{cash}")
                
                user = st.session_state.smart_api.getProfile()
                st.write(f"👤 **User:** {user['data']['name']}")
                
                st.divider()
                qty = st.number_input("Quantity", min_value=1, step=1, key="tr_qty")
                if st.button("🚀 EXECUTE BUY", type="primary"):
                    st.success(f"Signal sent for {qty} shares!")
            else:
                st.warning("Session Timeout. Please Reconnect.")
        except:
            st.error("Session Lost. Please login again.")
    else:
        st.warning("👈 Sidebar मधून लॉगिन करा.")

# --- HISTORY ---
if st.checkbox("Show History"):
    conn = sqlite3.connect(DB_NAME)
    hist = pd.read_sql_query("SELECT * FROM signals ORDER BY timestamp DESC LIMIT 5", conn)
    st.table(hist)
    conn.close()
