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
st.set_page_config(page_title="Oracle-X Pro v4.1", layout="wide")

API_KEY = 'jxsAJQD4'
CLIENT_ID = 'K52809090'

# --- UPDATED SESSION FUNCTION ---
def get_live_session(totp_key, pin):
    try:
        obj = SmartConnect(api_key=API_KEY)
        token = pyotp.TOTP(totp_key).now()
        data = obj.generateSession(CLIENT_ID, pin, token)
        
        if data and data.get('status'):
            # नवीन बदल: रिफ्रेश टोकन डिक्शनरीमध्ये सेव्ह करणे
            session_data = {
                "smart_api": obj,
                "refreshToken": data['data']['refreshToken']
            }
            return session_data
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
st.title("🔮 Oracle-X v4.1: API v2 Integrated")

# --- SIDEBAR ---
st.sidebar.header("🔐 Secure Login")
totp_val = st.sidebar.text_input("Enter TOTP QR Key", type="password", key="v41_totp")
pin_val = st.sidebar.text_input("Enter 4-Digit PIN", type="password", key="v41_pin")

# --- MAIN INTERFACE ---
ticker = st.text_input("Symbol (NSE)", value="RELIANCE.NS")
col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🔍 Run AI Analysis"):
        with st.spinner("Fetching Data..."):
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

with col2:
    st.subheader("💼 Trading Panel")
    
    if totp_val and pin_val:
        if st.button("💰 FETCH LIVE DATA / LOGIN", type="secondary"):
            with st.spinner("Connecting..."):
                session_dict = get_live_session(totp_val, pin_val)
                
                if session_dict:
                    try:
                        smart_api = session_dict["smart_api"]
                        r_token = session_dict["refreshToken"]
                        
                        # बदल: आता getProfile ला refreshToken पास करणे
                        user_resp = smart_api.getProfile(r_token)
                        profile_resp = smart_api.rmsLimit()
                        
                        if user_resp and user_resp.get('status'):
                            user_name = user_resp.get('data', {}).get('name', 'Trader')
                            cash = profile_resp.get('data', {}).get('availablecash', '0.00')
                            
                            st.success(f"👤 Welcome, {user_name}!")
                            st.info(f"💰 **Margin:** ₹{cash}")
                        else:
                            st.error("डेटा मिळाला नाही.")
                    except Exception as e:
                        st.error(f"API Error: {str(e)}")
                else:
                    st.error("लॉगिन अयशस्वी.")
        
        st.divider()
        qty = st.number_input("Quantity", min_value=1, step=1, key="qty_v41")
        if st.button("🚀 EXECUTE BUY ORDER", type="primary"):
            st.balloons()
            st.success("Buy signal processed!")
    else:
        st.warning("👈 Sidebar मध्ये TOTP आणि PIN टाका.")
