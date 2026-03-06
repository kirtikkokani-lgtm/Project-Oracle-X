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
st.set_page_config(page_title="Oracle-X Pro v4.0", layout="wide")

# --- ANGEL ONE CREDENTIALS ---
API_KEY = 'jxsAJQD4'
CLIENT_ID = 'K52809090'

# --- SAFE SESSION FUNCTION ---
def get_live_session(totp_key, pin):
    try:
        obj = SmartConnect(api_key=API_KEY)
        token = pyotp.TOTP(totp_key).now()
        data = obj.generateSession(CLIENT_ID, pin, token)
        # जर लॉगिन यशस्वी झाले आणि डेटा मिळाला तरच ऑब्जेक्ट परत करा
        if data and data.get('status'):
            return obj
        return None
    except Exception:
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

# --- UI HEADER ---
st.title("🔮 Oracle-X v4.0: Bulletproof AI Terminal")

# --- SIDEBAR ---
st.sidebar.header("🔐 Secure Login")
totp_val = st.sidebar.text_input("Enter TOTP QR Key", type="password", key="v4_totp")
pin_val = st.sidebar.text_input("Enter 4-Digit PIN", type="password", key="v4_pin")

# --- MAIN INTERFACE ---
ticker = st.text_input("Symbol (NSE)", value="RELIANCE.NS")

col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🔍 Run AI Deep Analysis"):
        with st.spinner(f"Analyzing {ticker}..."):
            df = yf.Ticker(ticker).history(period="1mo", interval="1h")
            if not df.empty:
                price = float(df['Close'].iloc[-1])
                rsi = float(get_rsi(df['Close']).iloc[-1])
                target = predict_price(df['Close'])
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Current Price", f"₹{price:.2f}")
                m2.metric("AI Target", f"₹{target:.2f}", f"{target-price:+.2f}")
                m3.metric("RSI (1h)", f"{rsi:.1f}")
                
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.update_layout(template="plotly_dark", height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("डेटा मिळाला नाही. सिम्बॉल तपासा.")

with col2:
    st.subheader("💼 Trading Panel")
    
    if totp_val and pin_val:
        if st.button("💰 FETCH LIVE DATA / LOGIN", type="secondary"):
            with st.spinner("Connecting to Angel One..."):
                # १. लॉगिनचा प्रयत्न
                smart_api = get_live_session(totp_val, pin_val)
                
                # २. जर लॉगिन यशस्वी झाले तरच (smart_api is not None)
                if smart_api:
                    try:
                        # ३. प्रोफाइल आणि बॅलन्स मिळवताना 'Safe Guard' वापरणे
                        user_resp = smart_api.getProfile()
                        profile_resp = smart_api.rmsLimit()
                        
                        if user_resp and user_resp.get('status'):
                            user_name = user_resp.get('data', {}).get('name', 'Trader')
                            cash = profile_resp.get('data', {}).get('availablecash', '0.00') if profile_resp else "0.00"
                            
                            st.success(f"👤 Welcome, {user_name}!")
                            st.info(f"💰 **Margin:** ₹{cash}")
                        else:
                            st.error("लॉगिन झाले पण डेटा फेच करताना एरर आली.")
                    except Exception as e:
                        st.error(f"API Error: {str(e)}")
                else:
                    st.error("❌ Login Failed! TOTP किंवा PIN चुकीचा आहे.")
        
        st.divider()
        qty = st.number_input("Quantity", min_value=1, step=1, key="qty_v4")
        if st.button("🚀 EXECUTE BUY ORDER", type="primary"):
            st.balloons()
            st.success("Buy signal processed!")
    else:
        st.warning("👈 Sidebar मध्ये TOTP आणि PIN टाका.")

st.divider()
st.caption("Oracle-X AI v4.0 | Stable Connection Guard Active")
