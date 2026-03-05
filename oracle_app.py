import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import requests
from bs4 import BeautifulSoup
from sklearn.linear_model import LinearRegression
import numpy as np
import sqlite3
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle-X Pro (DB)", layout="wide")
analyzer = SentimentIntensityAnalyzer()

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('oracle_data.db')
    c = conn.cursor()
    # सिग्नल्स सेव्ह करण्यासाठी टेबल
    c.execute('''CREATE TABLE IF NOT EXISTS signals 
                 (timestamp TEXT, ticker TEXT, price REAL, rsi REAL, signal TEXT)''')
    conn.commit()
    conn.close()

def save_signal_to_db(ticker, price, rsi, signal):
    try:
        conn = sqlite3.connect('oracle_data.db')
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO signals VALUES (?, ?, ?, ?, ?)", (now, ticker, price, rsi, signal))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Database Error: {e}")

# डेटाबेस तयार करणे
init_db()

# --- UTILITY FUNCTIONS ---
def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_live_news(stock_name):
    url = f"https://www.google.com/search?q={stock_name}+stock+news&tbm=nws"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = [g.get_text() for g in soup.find_all('div', class_='BNeaW vvjwJb AP7Wnd')]
        return headlines[:5]
    except: return []

def predict_next_day(df):
    data = df.reset_index()
    data['Day_Num'] = data.index
    model = LinearRegression().fit(data[['Day_Num']].values, data['Close'].values)
    pred = model.predict(np.array([[len(data)]]))
    return float(pred[0].item())

# --- UI LAYOUT ---
st.title("🔮 Oracle-X: Database Integrated Intelligence")
st.sidebar.header("🎛️ Control Panel")

# Inputs
ticker = st.sidebar.text_input("Single Ticker (NSE)", value="RELIANCE.NS")
company = st.sidebar.text_input("Company Name", value="Reliance Industries")

# Watchlist for Scanner
watchlist = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "TATAMOTORS.NS", "ICICIBANK.NS", "SBIN.NS", "ITC.NS", "ADANIENT.NS", "BHARTIARTL.NS"]

# --- ACTION 1: SINGLE STOCK SCAN ---
if st.sidebar.button("🔍 Deep Analysis"):
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)
    df['RSI'] = calculate_rsi(df['Close'])
    
    # Sentiment & Prediction
    headlines = get_live_news(company)
    sentiment = sum([analyzer.polarity_scores(h)['compound'] for h in headlines]) / len(headlines) if headlines else 0
    pred_price = predict_next_day(df)
    curr_price = float(df['Close'].iloc[-1])
    rsi_val = float(df['RSI'].iloc[-1])

    # Plot
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    st.plotly_chart(fig, use_container_width=True)

    # Logic & Database Save
    signal = "NEUTRAL ⏳"
    if rsi_val < 40 and sentiment > 0.1:
        signal = "STRONG BUY 🚀"
        st.success(f"{signal} | Target: ₹{pred_price:.2f}")
    elif rsi_val > 65 and sentiment < -0.1:
        signal = "STRONG SELL 🔥"
        st.error(f"{signal} | Target: ₹{pred_price:.2f}")
    
    save_signal_to_db(ticker, curr_price, rsi_val, signal)

# --- ACTION 2: MULTI-STOCK SCANNER ---
if st.sidebar.button("🚀 Run Multi-Stock Scanner"):
    st.subheader("📊 Market-Wide Opportunities")
    results = []
    
    for t in watchlist:
        try:
            d = yf.download(t, period="1mo", interval="1d", progress=False)
            d['RSI'] = calculate_rsi(d['Close'])
            l_price = float(d['Close'].iloc[-1])
            l_rsi = float(d['RSI'].iloc[-1])
            
            sig = "HOLD 🟡"
            if l_rsi < 38: sig = "BUY 🚀"
            elif l_rsi > 68: sig = "SELL 🔥"
            
            results.append({"Ticker": t, "Price": f"₹{l_price:.2f}", "RSI": f"{l_rsi:.1f}", "Signal": sig})
            
            # महत्त्वाचे सिग्नल्स डेटाबेसमध्ये सेव्ह करा
            if sig != "HOLD 🟡":
                save_signal_to_db(t, l_price, l_rsi, sig)
        except: continue

    st.table(pd.DataFrame(results))

# --- ACTION 3: VIEW HISTORY ---
st.divider()
st.header("📜 Trading Signals History")
if st.button("🔄 Refresh History"):
    conn = sqlite3.connect('oracle_data.db')
    try:
        history_df = pd.read_sql_query("SELECT * FROM signals ORDER BY timestamp DESC LIMIT 20", conn)
        st.dataframe(history_df, use_container_width=True)
    except:
        st.write("अजून कोणताही डेटा सेव्ह झालेला नाही.")
    finally:
        conn.close()
