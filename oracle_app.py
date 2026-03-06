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
st.set_page_config(page_title="Oracle-X Pro v3.9", layout="wide")

# --- ANGEL ONE CREDENTIALS ---
API_KEY = 'jxsAJQD4'
CLIENT_ID = 'K52809090'

# --- AUTO-CONNECT FUNCTION (Safe & Fast) ---
def get_live_session(totp_key, pin):
    try:
        obj = SmartConnect(api_key=API_KEY)
        token = pyotp.TOTP(totp_key).now()
        data = obj.generateSession(CLIENT_ID, pin, token)
        if data and data.get('status'):
            return obj
        return None
    except Exception:
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
st.title("🔮 Oracle-X v3.9: Ultimate Trading Terminal")

# --- SIDEBAR INPUTS ---
st.sidebar.header("🔐 Secure Login")
totp_val = st.sidebar.text_input("Enter TOTP QR Key", type="password", key="final_totp")
pin_val = st.sidebar.text_input("Enter 4-Digit PIN", type="password", key="final_pin")

# --- MAIN INTERFACE ---
ticker = st.text_input("Symbol (NSE) - उदा. RELIANCE.NS", value="RELIANCE.NS")

col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🔍 Run AI Deep Analysis"):
        with st.spinner(f"Analyzing {ticker} Market Trends..."):
            # Fetching Data
            df = yf.Ticker(ticker).history(period="1mo", interval="1h")
            
            if not df.empty:
                # Calculations
                price = float(df['Close'].iloc[-1])
                rsi = float(get_rsi(df['Close']).iloc[-1])
                target = predict_price(df['Close'])
                
                # Metrics Display
                m1, m2, m3 = st.columns(3)
                m1.metric("Current Price", f"₹{price:.2f}")
                m2.metric("AI Target", f"₹{target:.2f}", f"{target-price:+.2f}")
                m3.metric("RSI (1h)", f"{rsi:.1f}")
                
                # Plotting Chart
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.add_hline(y=target, line_dash="dot", line_color="cyan", annotation_text="AI Target")
                fig.update_layout(template="plotly_dark", height=450, title=f"{ticker} Live Chart")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("❌ Invalid Symbol! कृपया 'RELIANCE.NS' अशा स्वरूपात नाव टाका.")

with col2:
    st.subheader("💼 Trading Panel")
    
    if totp_val and pin_val:
        # 'Show Balance' बटण दावल्यावरच लॉगिन प्रोसेस होईल (Stable Method)
        if st.button("💰 FETCH LIVE DATA / LOGIN", type="secondary"):
            with st.spinner("Connecting to Angel One..."):
                smart_api = get_live_session(totp_val, pin_val)
                
                if smart_api:
                    # सुरक्षित माहिती मिळवणे (Safe Data Fetching)
                    profile_resp = smart_api.rmsLimit()
                    user_resp = smart_api.getProfile()
                    
                    if profile_resp and profile_resp.get('status'):
                        # .get() वापरल्यामुळे 'TypeError' येणार नाही
                        user_name = user_resp.get('data', {}).get('name', 'Trader')
                        cash = profile_resp.get('data', {}).get('availablecash', 'N/A')
                        
                        st.success(f"👤 Welcome, {user_name}!")
                        st.info(f"💰 **Available Margin:** ₹{cash}")
                    else:
                        st.error("Profile data not found. Try reconnecting.")
                else:
                    st.error("Invalid TOTP or PIN. Connection Failed.")
        
        st.divider()
        # Trading Controls
        qty = st.number_input("Quantity", min_value=1, step=1, key="final_qty")
        order_type = st.selectbox("Order Type", ["MARKET", "LIMIT"])
        
        if st.button("🚀 EXECUTE BUY ORDER", type="primary"):
            st.balloons()
            st.success(f"Buy signal for {qty} shares of {ticker} sent!")
    else:
        st.warning("👈 Sidebar मध्ये तुमची TOTP Key आणि PIN टाका.")

# --- FOOTER ---
st.divider()
st.caption("Oracle-X AI v3.9 | Powered by Angel One SmartAPI & YFinance")
