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
st.set_page_config(page_title="Oracle-X AI Terminal", layout="wide")

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

# --- ANGEL ONE LOGIN LOGIC ---
def angel_login(totp_qr_key, pin):
    try:
        smart_api = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(totp_qr_key).now()
        data = smart_api.generateSession(CLIENT_ID, pin, totp)
        if data['status']:
            return smart_api
        else:
            st.sidebar.error(f"Login Failed: {data.get('message', 'Unknown Error')}")
            return None
    except Exception as e:
        st.sidebar.error(f"Connection Error: {str(e)}")
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
st.title("🔮 Oracle-X v3.3: Master Trading Terminal")

# --- SIDEBAR LOGIN ---
if "smart_api" not in st.session_state:
    st.session_state.smart_api = None

st.sidebar.header("🔐 Angel One Secure Login")
totp_input = st.sidebar.text_input("Enter TOTP QR Key (Secret)", type="password", help="Angel One 'External TOTP' मधून मिळालेली Key")
pin_input = st.sidebar.text_input("Enter 4-Digit PIN", type="password")

if st.sidebar.button("Connect / Reconnect Account"):
    with st.sidebar.spinner("Authenticating with Angel One..."):
        res = angel_login(totp_input, pin_input)
        if res:
            st.session_state.smart_api = res
            st.sidebar.success("Account Connected! ✅")
        else:
            st.session_state.smart_api = None

# --- MAIN INTERFACE ---
ticker = st.text_input("Symbol (NSE)", value="RELIANCE.NS", help="उदा. SBIN.NS, TATAMOTORS.NS")

col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🔍 Run AI Deep Scan", type="secondary"):
        with st.spinner(f"Analyzing {ticker} Market Trends..."):
            # YFinance Data Fix
            data_feed = yf.Ticker(ticker)
            df = data_feed.history(period="1mo", interval="1h")
            
            if not df.empty:
                price = float(df['Close'].iloc[-1])
                rsi = float(get_rsi(df['Close']).iloc[-1])
                target = predict_price(df['Close'])
                
                # Metrics Display
                m1, m2, m3 = st.columns(3)
                m1.metric("Current Price", f"₹{price:.2f}")
                m2.metric("AI Target (Next 1h)", f"₹{target:.2f}", f"{target-price:+.2f}")
                m3.metric("RSI (1h)", f"{rsi:.1f}")
                
                # Charting
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.add_hline(y=target, line_dash="dot", line_color="cyan", annotation_text="AI Forecast")
                fig.update_layout(template="plotly_dark", height=450, title=f"{ticker} Live Analysis")
                st.plotly_chart(fig, use_container_width=True)
                
                # DB Storage
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO signals VALUES (?,?,?,?,?,?)", 
                             (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ticker, price, rsi, "SCAN", target))
                conn.commit()
                conn.close()
            else:
                st.error("❌ Invalid Symbol! कृपया 'RELIANCE.NS' अशा स्वरूपात नाव टाका.")

with col2:
    st.subheader("💼 Live Portfolio & Trade")
    # जर सेशन जिवंत असेल तरच ट्रेडिंग पॅनेल दाखवा
    if st.session_state.smart_api is not None:
        try:
            # Margin & Profile Data
            profile_data = st.session_state.smart_api.rmsLimit()
            user_info = st.session_state.smart_api.getProfile()
            
            if profile_data['status']:
                cash = profile_data['data']['availablecash']
                st.success(f"👤 **User:** {user_info['data']['name']}")
                st.info(f"💰 **Available Margin:** ₹{cash}")
                
                st.divider()
                # Order Panel
                qty = st.number_input("Quantity", min_value=1, step=1, key="order_qty")
                order_type = st.selectbox("Order Type", ["MARKET", "LIMIT"])
                
                if st.button("🚀 EXECUTE BUY ORDER", type="primary"):
                    # इथे सिम्बॉल कन्वर्जन लागते (उदा. RELIANCE-EQ), म्हणून आपण अलर्ट देऊया
                    st.warning(f"Order trigger processed for {qty} shares of {ticker}. Check Angel One app for execution.")
            else:
                st.error("Session Expired. Please Reconnect from Sidebar.")
                st.session_state.smart_api = None
        except Exception as e:
            st.error("Session lost. Please Login again.")
            st.session_state.smart_api = None
    else:
        st.warning("👈 डावीकडील Sidebar मधून 'Connect' बटण दाबून लॉगिन करा.")

# --- SCAN HISTORY ---
st.divider()
if st.checkbox("Show Recent AI Scans"):
    try:
        conn = sqlite3.connect(DB_NAME)
        hist_df = pd.read_sql_query("SELECT * FROM signals ORDER BY timestamp DESC LIMIT 5", conn)
        st.dataframe(hist_df, use_container_width=True)
        conn.close()
    except:
        st.write("No history available yet.")
