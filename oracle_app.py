import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from SmartApi import SmartConnect
import pyotp
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle-X Pro v3.8", layout="wide")

# --- ANGEL ONE CREDENTIALS ---
API_KEY = 'jxsAJQD4'
CLIENT_ID = 'K52809090'

# --- AUTO-CONNECT FUNCTION ---
# हे फंक्शन दरवेळी सुरक्षितपणे लॉगिन तपासेल
def get_live_session(totp_key, pin):
    try:
        obj = SmartConnect(api_key=API_KEY)
        token = pyotp.TOTP(totp_key).now()
        data = obj.generateSession(CLIENT_ID, pin, token)
        if data['status']:
            return obj
        return None
    except:
        return None

# --- AI LOGIC ---
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

# --- UI ---
st.title("🔮 Oracle-X v3.8: Direct Connect Terminal")

# Sidebar - इथे आपण फक्त व्हॅल्यूज सेव्ह करू
st.sidebar.header("🔐 Secure Login")
totp_val = st.sidebar.text_input("Enter TOTP QR Key", type="password", key="s_totp")
pin_val = st.sidebar.text_input("Enter 4-Digit PIN", type="password", key="s_pin")

# --- MAIN INTERFACE ---
ticker = st.text_input("Symbol (NSE)", value="RELIANCE.NS")

col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🔍 Run AI Analysis"):
        with st.spinner(f"Analyzing {ticker}..."):
            df = yf.Ticker(ticker).history(period="1mo", interval="1h")
            if not df.empty:
                price = float(df['Close'].iloc[-1])
                rsi = float(get_rsi(df['Close']).iloc[-1])
                target = predict_price(df['Close'])
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Price", f"₹{price:.2f}")
                m2.metric("Target", f"₹{target:.2f}", f"{target-price:+.2f}")
                m3.metric("RSI", f"{rsi:.1f}")
                
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.update_layout(template="plotly_dark", height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("Data Fetch Error.")

with col2:
    st.subheader("💼 Trading Panel")
    
    if totp_val and pin_val:
        # दरवेळी नवीन सेशन घेण्याऐवजी फक्त डेटा दाखवताना लॉगिन करणे
        if st.button("💰 SHOW BALANCE / LOGIN"):
            with st.spinner("Connecting to Angel One..."):
                smart_api = get_live_session(totp_val, pin_val)
                if smart_api:
                    profile = smart_api.rmsLimit()
                    user = smart_api.getProfile()
                    if profile['status']:
                        st.success(f"👤 {user['data']['name']}")
                        st.info(f"💰 **Margin:** ₹{profile['data']['availablecash']}")
                        st.session_state.logged_in = True
                    else:
                        st.error("Session Failed.")
                else:
                    st.error("Invalid TOTP or PIN.")
        
        st.divider()
        qty = st.number_input("Quantity", min_value=1, step=1)
        if st.button("🚀 EXECUTE BUY", type="primary"):
            st.balloons()
            st.success("Buy Signal Processed!")
    else:
        st.warning("👈 Enter TOTP & PIN in Sidebar first.")
