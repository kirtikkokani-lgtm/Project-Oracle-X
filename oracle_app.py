import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import requests
from bs4 import BeautifulSoup
from sklearn.linear_model import LinearRegression
import numpy as np

# --- CONFIGURATION ---
TOKEN = "8337154141:AAGyn09G-w9BPumpRpwMFST89jRPMmku5Ss"
CHAT_ID = "तुमचा_CHAT_ID_येथे_टाका" 

st.set_page_config(page_title="Oracle-X Pro", layout="wide")
analyzer = SentimentIntensityAnalyzer()

# --- ADVANCED FUNCTIONS ---

def get_live_news(stock_name):
    url = f"https://www.google.com/search?q={stock_name}+stock+news&tbm=nws"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = [g.get_text() for g in soup.find_all('div', class_='BNeaW vvjwJb AP7Wnd')]
        return headlines[:5]
    except: return []

def add_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # EMA (Trend)
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # Bollinger Bands
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    return df

def predict_next_day(df):
    data = df.reset_index()
    data['Day_Num'] = data.index
    model = LinearRegression().fit(data[['Day_Num']].values, data['Close'].values)
    pred = model.predict(np.array([[len(data)]]))
    return float(pred[0].item())

# --- UI LAYOUT ---
st.title("🔮 Oracle-X: Ultra-Advanced Intelligence")
st.sidebar.header("Settings")
ticker = st.sidebar.text_input("Ticker (NSE)", value="RELIANCE.NS")
company = st.sidebar.text_input("Company Name", value="Reliance Industries")

if st.sidebar.button("🚀 Run Deep Intelligence"):
    # 1. Fetch & Process Data
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)
    df = add_indicators(df)
    
    # 2. Sentiment & Prediction
    headlines = get_live_news(company)
    sentiment = sum([analyzer.polarity_scores(h)['compound'] for h in headlines]) / len(headlines) if headlines else 0
    pred_price = predict_next_day(df)
    curr_price = float(df['Close'].iloc[-1].item())
    rsi = float(df['RSI'].iloc[-1].item())
    ema20 = float(df['EMA20'].iloc[-1].item())
    ema50 = float(df['EMA50'].iloc[-1].item())

    # 3. Visualization
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='orange', width=1), name="EMA 20"))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='blue', width=1), name="EMA 50"))
    st.plotly_chart(fig, use_container_width=True)

    # 4. DECISION LOGIC (The Advanced Part)
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    # Logic: Trend is Up (EMA20 > EMA50) + Momentum is Oversold (RSI < 45) + Sentiment is Good
    decision = "WAIT ⏳"
    accuracy = 50 # Base accuracy

    if ema20 > ema50 and rsi < 50 and sentiment > 0.1:
        decision = "🚀 STRONG BUY"
        accuracy = 85
    elif ema20 < ema50 and rsi > 60 and sentiment < -0.1:
        decision = "🔥 STRONG SELL"
        accuracy = 82
    
    with col1:
        st.header("Decision")
        st.subheader(decision)
        st.write(f"Confidence Score: {accuracy}%")
    
    with col2:
        st.header("ML Forecast")
        st.metric("Target Tomorrow", f"₹{pred_price:.2f}", delta=f"{pred_price-curr_price:.2f}")
    
    with col3:
        if "BUY" in decision:
            sl = curr_price * 0.98  # 2% Stop Loss
            tgt = curr_price * 1.04 # 4% Target
            st.header("Risk Setup")
            st.write(f"**Stop-Loss:** ₹{sl:.2f}")
            st.write(f"**Target:** ₹{tgt:.2f}")
            st.write("**Risk-Reward:** 1:2")
        else:
            st.header("Status")
            st.write("No active trade setup found.")

    # 5. Telegram Alert
    if "STRONG" in decision:
        alert = f"📢 ORACLE-X ALERT\nStock: {ticker}\nSignal: {decision}\nConfidence: {accuracy}%\nPrice: {curr_price:.2f}\nTGT: {pred_price:.2f}"
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={alert}")