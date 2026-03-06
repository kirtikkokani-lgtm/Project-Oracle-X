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
st.set_page_config(page_title="Oracle-X Master AI", layout="wide")
analyzer = SentimentIntensityAnalyzer()

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('oracle_data.db')
    c = conn.cursor()
    # जुने टेबल काढून नवीन तयार करण्यासाठी ही ओळ वापरा (फक्त एकदाच)
    # c.execute('DROP TABLE IF EXISTS signals') 
    
    c.execute('''CREATE TABLE IF NOT EXISTS signals 
                 (timestamp TEXT, ticker TEXT, price REAL, rsi REAL, signal TEXT, target REAL)''')
    conn.commit()
    conn.close()

def save_signal_to_db(ticker, price, rsi, signal, target):
    try:
        conn = sqlite3.connect('oracle_data.db')
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO signals VALUES (?, ?, ?, ?, ?, ?)", (now, ticker, price, rsi, signal, target))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Database Error: {e}")

init_db()

# --- AI & TECHNICAL FUNCTIONS ---
def get_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def predict_next_price(series):
    y = series.values.reshape(-1, 1)
    X = np.arange(len(y)).reshape(-1, 1)
    model = LinearRegression().fit(X, y)
    next_index = np.array([[len(y)]])
    return float(model.predict(next_index)[0][0])

def get_live_news(stock_name):
    url = f"https://www.google.com/search?q={stock_name}+stock+news&tbm=nws"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = [g.get_text() for g in soup.find_all('div', class_='BNeaW vvjwJb AP7Wnd')]
        return headlines[:5]
    except: return []

# --- UI LAYOUT ---
st.title("🔮 Oracle-X: AI Intelligence Dashboard")
st.sidebar.header("🕹️ Control Room")

ticker = st.sidebar.text_input("Enter Ticker (NSE)", value="RELIANCE.NS")
company = st.sidebar.text_input("Company Name", value="Reliance Industries")
watchlist = ["RELIANCE.NS", "TCS.NS", "TATAMOTORS.NS", "SBIN.NS", "INFY.NS", "HDFCBANK.NS"]

# --- ACTION: DEEP AI ANALYSIS ---
if st.sidebar.button("🤖 Run AI Deep Scan"):
    with st.spinner("Analyzing Market Data..."):
        df = yf.download(ticker, period="1mo", interval="1h", progress=False)
        if not df.empty:
            curr_price = float(df['Close'].iloc[-1])
            rsi_val = float(get_rsi(df['Close']).iloc[-1])
            target_price = predict_next_price(df['Close'])
            
            # Sentiment Analysis
            news = get_live_news(company)
            sentiment = sum([analyzer.polarity_scores(n)['compound'] for n in news]) / len(news) if news else 0
            
            # Logic for Signal
            signal = "Neutral ⚪"
            if rsi_val < 38 and sentiment > 0.05: signal = "STRONG BUY 🚀"
            elif rsi_val > 68 and sentiment < -0.05: signal = "STRONG SELL 🔥"
            
            # Save to Database
            save_signal_to_db(ticker, curr_price, rsi_val, signal, target_price)
            
            # UI Display
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Price", f"₹{curr_price:.2f}")
            col2.metric("AI Target", f"₹{target_price:.2f}", f"{target_price-curr_price:+.2f}")
            col3.metric("RSI (1h)", f"{rsi_val:.1f}")

            # Plotting
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            fig.add_hline(y=target_price, line_dash="dot", line_color="green", annotation_text="AI Target")
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader(f"Strategy Signal: {signal}")
            st.write(f"**Sentiment Score:** {sentiment:.2f}")

# --- ACTION: VIEW STORED HISTORY ---
st.divider()
st.subheader("📜 AI Signal History & Database")
if st.button("🔄 Refresh Logs"):
    conn = sqlite3.connect('oracle_data.db')
    try:
        history_df = pd.read_sql_query("SELECT * FROM signals ORDER BY timestamp DESC", conn)
        st.dataframe(history_df, use_container_width=True)
        
        # Accuracy Chart
        if not history_df.empty:
            st.line_chart(history_df.set_index('timestamp')[['price', 'target']])
    except:
        st.write("No data available in database.")
    finally:
        conn.close()
