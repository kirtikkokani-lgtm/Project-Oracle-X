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
st.set_page_config(page_title="Oracle-X Pro v3.7", layout="wide")

# --- ANGEL ONE CREDENTIALS ---
API_KEY = 'jxsAJQD4'
CLIENT_ID = 'K52809090'

# --- PERSISTENT LOGIN CACHE ---
# हे फंक्शन एकदा लॉगिन झालं की ते पूर्ण ॲपसाठी मेमरीत लॉक करून ठेवतं
@st.cache_resource(show_spinner=False)
def get_angel_session(totp_key, pin):
    try:
        obj = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(totp_key).now()
        data = obj.generateSession(CLIENT_ID, pin, totp)
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
st.title("🔮 Oracle-X v3.7: Ultra-Stable Terminal")

# Sidebar Login
st.sidebar.header("🔐 Secure Login")
totp_input = st.sidebar.text_input("Enter TOTP QR Key", type="password")
pin_input = st.sidebar.text_input("Enter 4-Digit PIN", type="password")

# लॉगिन सेव्ह करण्यासाठी session_state वापरणे
if "api_obj" not in st.session_state:
    st.session_state.api_obj = None

if st.sidebar.button("Connect Account"):
    # कॅशमधून किंवा नवीन लॉगिन मिळवणे
    res = get_angel_session(totp_input, pin_input)
    if res:
        st.session_state.api_obj = res
        st.sidebar.success("Account Locked & Connected! ✅")
    else:
        st.sidebar.error("Invalid Credentials")

# --- MAIN INTERFACE ---
ticker = st.text_input("Symbol (NSE)", value="RELIANCE.NS")

col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🔍 Run AI Analysis"):
        with st.spinner(f"Fetching {ticker} Data..."):
            data_feed = yf.Ticker(ticker)
            df = data_feed.history(period="1mo", interval="1h")
            
            if not df.empty:
                # Calculations
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
            else:
                st.error("Ticker Error.")

with col2:
    st.subheader("💼 Trading Panel")
    # सेशनमधून ऑब्जेक्ट घेताना पुन्हा एकदा खात्री करणे
    smart_api = st.session_state.get('api_obj')
    
    if smart_api:
        try:
            # बॅलन्स आणि नाव दाखवणे
            profile = smart_api.rmsLimit()
            user = smart_api.getProfile()
            
            if profile['status']:
                st.success(f"👤 {user['data']['name']}")
                st.info(f"💰 **Available:** ₹{profile['data']['availablecash']}")
                
                st.divider()
                qty = st.number_input("Quantity", min_value=1, step=1, key="q_val")
                if st.button("🚀 EXECUTE BUY", type="primary"):
                    st.balloons()
                    st.success("Buy Signal Processed!")
            else:
                st.warning("Session Expired. Re-Connect from Sidebar.")
        except:
            # जर ऑब्जेक्ट मेमरीत असेल पण कनेक्शन तुटलं असेल तर:
            st.error("Connection Interrupted. Please click 'Connect' again.")
    else:
        st.warning("👈 Please login from Sidebar.")
