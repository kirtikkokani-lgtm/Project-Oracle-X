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
st.set_page_config(page_title="Oracle-X Pro", layout="wide")
analyzer = SentimentIntensityAnalyzer()

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
st.title("🔮 Oracle-X: Institutional Intelligence")
st.sidebar.header("🎛️ Control Panel")

# Inputs
ticker = st.sidebar.text_input("Single Ticker (NSE)", value="RELIANCE.NS")
company = st.sidebar.text_input("Company Name", value="Reliance Industries")

# Watchlist for Scanner
watchlist = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "TATAMOTORS.NS", "ICICIBANK.NS", "SBIN.NS", "ITC.NS", "ADANIENT.NS", "BHARTIARTL.NS"]

# --- ACTION 1: SINGLE STOCK DEEP SCAN ---
if st.sidebar.button("🔍 Deep Analysis (Selected Stock)"):
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)
    df['RSI'] = calculate_rsi(df['Close'])
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # Sentiment & Prediction
    headlines = get_live_news(company)
    sentiment = sum([analyzer.polarity_scores(h)['compound'] for h in headlines]) / len(headlines) if headlines else 0
    pred_price = predict_next_day(df)
    curr_price = float(df['Close'].iloc[-1])
    rsi_val = float(df['RSI'].iloc[-1])

    # Plot
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='orange', width=1.5), name="EMA 20"))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='blue', width=1.5), name="EMA 50"))
    st.plotly_chart(fig, use_container_width=True)

    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Current Price", f"₹{curr_price:.2f}")
    c2.metric("RSI (14D)", f"{rsi_val:.1f}")
    c3.metric("Sentiment Score", f"{sentiment:.2f}")

    # Logic
    st.divider()
    if rsi_val < 40 and sentiment > 0.1:
        st.success(f"🚀 **Signal: STRONG BUY** | Predicted Target: ₹{pred_price:.2f}")
    elif rsi_val > 65 and sentiment < -0.1:
        st.error(f"🔥 **Signal: STRONG SELL** | Predicted Target: ₹{pred_price:.2f}")
    else:
        st.info("⏳ **Signal: NEUTRAL** | Market is stabilizing.")

# --- ACTION 2: MULTI-STOCK SCANNER ---
if st.sidebar.button("🚀 Run Multi-Stock Scanner"):
    st.subheader("📊 Market-Wide Opportunities (Watchlist)")
    results = []
    
    progress_bar = st.progress(0)
    for index, t in enumerate(watchlist):
        try:
            d = yf.download(t, period="1mo", interval="1d", progress=False)
            d['RSI'] = calculate_rsi(d['Close'])
            l_price = d['Close'].iloc[-1]
            l_rsi = d['RSI'].iloc[-1]
            
            sig = "WAIT ⏳"
            if l_rsi < 38: sig = "BUY 🚀"
            elif l_rsi > 68: sig = "SELL 🔥"
            
            results.append({"Ticker": t, "Price": f"₹{l_price:.2f}", "RSI": f"{l_rsi:.1;f}", "Signal": sig})
        except: continue
        progress_bar.progress((index + 1) / len(watchlist))

    res_df = pd.DataFrame(results)
    
    # Styling Table
    def highlight_signal(val):
        color = 'green' if 'BUY' in val else 'red' if 'SELL' in val else 'black'
        return f'color: {color}; font-weight: bold'

    st.table(res_df) # सोप्या मांडणीसाठी table वापरला आहे
