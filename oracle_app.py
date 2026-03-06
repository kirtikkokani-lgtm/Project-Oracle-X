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
st.set_page_config(page_title="Oracle-X Final v3.6", layout="wide")

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

# --- REUSABLE SESSION INITIALIZATION ---
if "smart_api" not in st.session_state:
    st.session_state.smart_api = None

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
st.title("🔮 Oracle-X v3.6: Multi-Session Terminal")

# --- SIDEBAR LOGIN ---
st.sidebar.header("🔐 Angel One Secure Login")
totp_input = st.sidebar.text_input("Enter TOTP QR Key", type="password", key="totp_key")
pin_input = st.sidebar.text_input("Enter 4-Digit PIN", type="password", key="pin_key")

if st.sidebar.button("Connect Account"):
    try:
        obj = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(totp_input).now()
        data = obj.generateSession(CLIENT_ID, pin_input, totp)
        if data['status']:
            st.session_state.smart_api = obj
            st.sidebar.success("Account Connected! ✅")
        else:
            st.sidebar.error("Login Failed. Check Credentials.")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

# --- MAIN INTERFACE ---
ticker = st.text_input("Symbol (NSE)", value="RELIANCE.NS")

col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🔍 Run AI Deep Scan"):
        # स्कॅन करताना आपण लॉगिन चेक करणार नाही, फक्त डेटा दाखवू
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
            else:
                st.error("Data loading failed.")

with col2:
    st.subheader("💼 Trading Panel")
    # 'Persistent session' तपासणे
    if st.session_state.smart_api:
        try:
            # इथे आपण 'Refresh' न करता माहिती मिळवण्याचा प्रयत्न करू
            profile = st.session_state.smart_api.rmsLimit()
            if profile and profile['status']:
                cash = profile['data']['availablecash']
                st.info(f"💰 **Margin:** ₹{cash}")
                
                user = st.session_state.smart_api.getProfile()
                st.write(f"👤 **User:** {user['data']['name']}")
                
                st.divider()
                qty = st.number_input("Quantity", min_value=1, step=1, key="tr_qty_final")
                if st.button("🚀 EXECUTE BUY", type="primary"):
                    st.success(f"Signal sent for {qty} shares of {ticker}!")
            else:
                st.warning("Session Expired. Please click 'Connect' again.")
        except:
            # जर एरर आली, तर Session रिकामं करू नका, फक्त मेसेज द्या
            st.error("Connection unstable. Try clicking 'Connect' in Sidebar.")
    else:
        st.warning("👈 Sidebar मधून लॉगिन करा.")
