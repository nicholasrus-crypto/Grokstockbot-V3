
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="GrokStockBot",
    page_icon="📈",
    layout="wide"
)

# SESSION STATE
if "balance" not in st.session_state:
    st.session_state.balance = 3000.0

if "positions" not in st.session_state:
    st.session_state.positions = {}

if "history" not in st.session_state:
    st.session_state.history = []

if "running" not in st.session_state:
    st.session_state.running = False

# HEADER
st.title("🔴 GrokStockBot V2.0")
st.caption("AI-inspired algorithmic trading dashboard | Paper trading")

# SIDEBAR
st.sidebar.header("Control Center")

symbol = st.sidebar.selectbox(
    "Trading asset",
    ["AAPL", "MSFT", "NVDA", "SPY"]
)

period = st.sidebar.selectbox(
    "Market history",
    ["1mo", "3mo", "6mo", "1y", "2y"]
)

risk_percent = st.sidebar.slider(
    "Maximum position size (%)",
    1, 20, 10
)

daily_limit = st.sidebar.slider(
    "Daily loss limit (%)",
    1, 5, 2
)

if st.sidebar.button("🛑 EMERGENCY STOP"):
    st.session_state.running = False
    st.error("Trading stopped.")

# MARKET DATA
@st.cache_data(ttl=60)
def get_market_data(ticker, history):
    data = yf.download(
        ticker,
        period=history,
        interval="1d",
        auto_adjust=True,
        progress=False
    )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if data.empty:
        return pd.DataFrame()

    data["SMA20"] = data["Close"].rolling(20).mean()
    data["SMA50"] = data["Close"].rolling(50).mean()

    delta = data["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/14,
        min_periods=14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/14,
        min_periods=14,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    data["RSI"] = 100 - (100 / (1 + rs))

    return data.dropna(subset=["Close"])

st.header("Market Overview")

try:
    data = get_market_data(symbol, period)

    if data.empty:
        st.error("No market data available.")
        st.stop()

    price = float(data["Close"].iloc[-1])

    sma20 = data["SMA20"].iloc[-1]
    sma50 = data["SMA50"].iloc[-1]
    rsi = data["RSI"].iloc[-1]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Current price", f"${price:.2f}")
    col2.metric("SMA 20", f"${sma20:.2f}")
    col3.metric("SMA 50", f"${sma50:.2f}")
    col4.metric("RSI", f"{rsi:.2f}")

    # STRATEGY
    if pd.isna(rsi):
        signal = "WAIT"
    elif sma20 > sma50 and rsi < 70:
        signal = "BUY"
    elif sma20 < sma50 or rsi > 70:
        signal = "SELL"
    else:
        signal = "WAIT"

    st.subheader("Trading Signal")

    if signal == "BUY":
        st.success("BUY SIGNAL")
    elif signal == "SELL":
        st.error("SELL SIGNAL")
    else:
        st.warning("WAIT")

    # CHART
    chart = go.Figure()

    chart.add_trace(go.Scatter(
        x=data.index,
        y=data["Close"],
        name="Price"
    ))

    chart.add_trace(go.Scatter(
        x=data.index,
        y=data["SMA20"],
        name="SMA 20"
    ))

    chart.add_trace(go.Scatter(
        x=data.index,
        y=data["SMA50"],
        name="SMA 50"
    ))

    chart.update_layout(
        title=f"{symbol} Market Analysis",
        template="plotly_dark",
        height=450
    )

    st.plotly_chart(chart, use_container_width=True)

    # PAPER TRADING
    st.header("Paper Trading")

    col1, col2 = st.columns(2)

    col1.metric(
        "Available cash",
        f"${st.session_state.balance:,.2f}"
    )

    st.write("Initial simulated capital: $3,000")

    quantity = st.number_input(
        "Quantity",
        min_value=1,
        max_value=1000,
        value=1
    )

    max_position = (
        st.session_state.balance *
        risk_percent / 100
    )

    if st.button("BUY (SIMULATED)"):
        cost = quantity * price

        if cost > max_position:
            st.error("Position exceeds configured risk limit.")

        elif cost > st.session_state.balance:
            st.error("Insufficient simulated cash.")

        else:
            st.session_state.balance -= cost

            st.session_state.positions[symbol] = (
                st.session_state.positions.get(symbol, 0)
                + quantity
            )

            st.session_state.history.append({
                "Date": datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "Asset": symbol,
                "Action": "BUY",
                "Quantity": quantity,
                "Price": price
            })

            st.success("Simulated purchase completed.")

    if st.button("SELL (SIMULATED)"):
        owned = st.session_state.positions.get(symbol, 0)

        if quantity > owned:
            st.error("You do not own enough shares.")

        else:
            proceeds = quantity * price

            st.session_state.balance += proceeds

            st.session_state.positions[symbol] -= quantity

            st.session_state.history.append({
                "Date": datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "Asset": symbol,
                "Action": "SELL",
                "Quantity": quantity,
                "Price": price
            })

            st.success("Simulated sale completed.")

    # PORTFOLIO
    st.header("Portfolio")

    portfolio = []

    for asset, qty in st.session_state.positions.items():
        if qty > 0:
            portfolio.append({
                "Asset": asset,
                "Shares": qty,
                "Market Value": round(
                    qty * price if asset == symbol else 0,
                    2
                )
            })

    if portfolio:
        st.dataframe(
            pd.DataFrame(portfolio),
            use_container_width=True
        )
    else:
        st.info("No open positions.")

    # HISTORY
    st.header("Trading History")

    if st.session_state.history:
        st.dataframe(
            pd.DataFrame(st.session_state.history),
            use_container_width=True
        )
    else:
        st.info("No trades yet.")

except Exception as error:
    st.error(f"Market data error: {error}")

st.caption(
    "GrokStockBot V2.0 | Simulation only | "
    "Not financial advice"
)
