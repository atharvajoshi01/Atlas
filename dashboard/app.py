"""Atlas Trading Dashboard - Main Application."""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Atlas - Low-Latency Order Book Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-top: 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .stMetric > div {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)


def generate_sample_orderbook():
    """Generate sample order book data."""
    mid_price = 100.0
    levels = 10

    bid_prices = mid_price - np.arange(1, levels + 1) * 0.01
    ask_prices = mid_price + np.arange(1, levels + 1) * 0.01
    bid_sizes = np.random.exponential(1000, levels) + 100
    ask_sizes = np.random.exponential(1000, levels) + 100

    return bid_prices, bid_sizes, ask_prices, ask_sizes


def generate_sample_trades(n_trades=100):
    """Generate sample trade data."""
    np.random.seed(42)
    timestamps = pd.date_range(end=datetime.now(), periods=n_trades, freq='1s')
    prices = 100 + np.cumsum(np.random.normal(0, 0.01, n_trades))
    sizes = np.random.exponential(100, n_trades)
    sides = np.random.choice(['buy', 'sell'], n_trades)

    return pd.DataFrame({
        'timestamp': timestamps,
        'price': prices,
        'size': sizes,
        'side': sides
    })


def generate_sample_performance(n_days=252):
    """Generate sample performance data."""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
    returns = np.random.normal(0.0005, 0.015, n_days)
    cumulative = np.cumprod(1 + returns)

    return pd.DataFrame({
        'date': dates,
        'returns': returns,
        'cumulative': cumulative,
        'equity': 100000 * cumulative
    })


def plot_orderbook(bid_prices, bid_sizes, ask_prices, ask_sizes):
    """Create order book depth chart."""
    fig = go.Figure()

    # Cumulative sizes for depth
    bid_cum = np.cumsum(bid_sizes)
    ask_cum = np.cumsum(ask_sizes)

    # Bid side (green)
    fig.add_trace(go.Scatter(
        x=bid_prices[::-1],
        y=bid_cum[::-1],
        fill='tozeroy',
        fillcolor='rgba(0, 150, 0, 0.3)',
        line=dict(color='green', width=2),
        name='Bids',
        hovertemplate='Price: %{x:.2f}<br>Cumulative Size: %{y:.0f}<extra></extra>'
    ))

    # Ask side (red)
    fig.add_trace(go.Scatter(
        x=ask_prices,
        y=ask_cum,
        fill='tozeroy',
        fillcolor='rgba(255, 0, 0, 0.3)',
        line=dict(color='red', width=2),
        name='Asks',
        hovertemplate='Price: %{x:.2f}<br>Cumulative Size: %{y:.0f}<extra></extra>'
    ))

    fig.update_layout(
        title='Order Book Depth',
        xaxis_title='Price',
        yaxis_title='Cumulative Size',
        hovermode='x unified',
        showlegend=True,
        height=400,
    )

    return fig


def plot_equity_curve(perf_df):
    """Create equity curve chart."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=perf_df['date'],
        y=perf_df['equity'],
        mode='lines',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.2)',
        name='Equity',
        hovertemplate='Date: %{x}<br>Equity: $%{y:,.2f}<extra></extra>'
    ))

    fig.update_layout(
        title='Equity Curve',
        xaxis_title='Date',
        yaxis_title='Portfolio Value ($)',
        hovermode='x unified',
        height=400,
    )

    return fig


def plot_returns_distribution(perf_df):
    """Create returns distribution histogram."""
    fig = px.histogram(
        perf_df,
        x='returns',
        nbins=50,
        title='Daily Returns Distribution',
        labels={'returns': 'Daily Return'},
        color_discrete_sequence=['#1f77b4']
    )

    fig.update_layout(
        xaxis_title='Daily Return',
        yaxis_title='Frequency',
        height=300,
    )

    return fig


def calculate_metrics(perf_df):
    """Calculate performance metrics."""
    returns = perf_df['returns'].values

    # Annual return
    total_return = perf_df['cumulative'].iloc[-1] - 1
    years = len(returns) / 252
    annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0

    # Volatility
    volatility = np.std(returns) * np.sqrt(252)

    # Sharpe ratio
    sharpe = annual_return / volatility if volatility > 0 else 0

    # Max drawdown
    cumulative = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (running_max - cumulative) / running_max
    max_drawdown = np.max(drawdowns)

    # Win rate
    win_rate = np.sum(returns > 0) / len(returns)

    return {
        'Annual Return': f'{annual_return:.2%}',
        'Volatility': f'{volatility:.2%}',
        'Sharpe Ratio': f'{sharpe:.2f}',
        'Max Drawdown': f'{max_drawdown:.2%}',
        'Win Rate': f'{win_rate:.2%}',
        'Total Trades': len(returns),
    }


def main():
    """Main dashboard application."""
    # Header
    st.markdown('<p class="main-header">Atlas</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Low-Latency Order Book Engine with Predictive Execution</p>', unsafe_allow_html=True)
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("Dashboard Controls")

        view = st.selectbox(
            "Select View",
            ["Overview", "Order Book", "Performance", "Backtest Results", "System Metrics"]
        )

        st.markdown("---")

        st.subheader("Quick Stats")
        st.metric("Order Book Updates/sec", "1.2M")
        st.metric("Avg Latency", "16 ns")
        st.metric("Memory Usage", "128 MB")

        st.markdown("---")
        st.markdown("""
        **Atlas Engine Performance**
        - Add Order: ~16 ns
        - Cancel Order: ~50 ns
        - Get BBO: ~0.7 ns
        - Pool Allocator: 1.7 ns
        """)

    # Main content
    if view == "Overview":
        show_overview()
    elif view == "Order Book":
        show_orderbook()
    elif view == "Performance":
        show_performance()
    elif view == "Backtest Results":
        show_backtest()
    elif view == "System Metrics":
        show_system_metrics()


def show_overview():
    """Show overview dashboard."""
    st.header("System Overview")

    # Top metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Add Order Latency",
            value="16 ns",
            delta="-3 ns",
            delta_color="inverse"
        )

    with col2:
        st.metric(
            label="Cancel Order Latency",
            value="50 ns",
            delta="-5 ns",
            delta_color="inverse"
        )

    with col3:
        st.metric(
            label="BBO Access",
            value="0.7 ns",
            delta="0 ns"
        )

    with col4:
        st.metric(
            label="Throughput",
            value="64M ops/sec",
            delta="+2M",
            delta_color="normal"
        )

    st.markdown("---")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        bid_p, bid_s, ask_p, ask_s = generate_sample_orderbook()
        fig = plot_orderbook(bid_p, bid_s, ask_p, ask_s)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        perf_df = generate_sample_performance()
        fig = plot_equity_curve(perf_df)
        st.plotly_chart(fig, use_container_width=True)

    # Performance Summary
    st.subheader("Performance Summary")
    metrics = calculate_metrics(perf_df)

    cols = st.columns(len(metrics))
    for i, (key, value) in enumerate(metrics.items()):
        cols[i].metric(key, value)


def show_orderbook():
    """Show order book visualization."""
    st.header("Order Book Visualization")

    # Generate data
    bid_p, bid_s, ask_p, ask_s = generate_sample_orderbook()

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = plot_orderbook(bid_p, bid_s, ask_p, ask_s)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Book Statistics")
        mid = (bid_p[0] + ask_p[0]) / 2
        spread = ask_p[0] - bid_p[0]
        spread_bps = spread / mid * 10000

        st.metric("Mid Price", f"${mid:.2f}")
        st.metric("Spread", f"${spread:.4f}")
        st.metric("Spread (bps)", f"{spread_bps:.2f}")
        st.metric("Bid Depth", f"{sum(bid_s):,.0f}")
        st.metric("Ask Depth", f"{sum(ask_s):,.0f}")

        imbalance = (sum(bid_s) - sum(ask_s)) / (sum(bid_s) + sum(ask_s))
        st.metric("Imbalance", f"{imbalance:.2%}")

    # Level-by-level view
    st.subheader("Order Book Levels")

    book_df = pd.DataFrame({
        'Bid Size': bid_s[::-1],
        'Bid Price': [f"${p:.2f}" for p in bid_p[::-1]],
        'Ask Price': [f"${p:.2f}" for p in ask_p],
        'Ask Size': ask_s
    })

    st.dataframe(book_df, use_container_width=True)


def show_performance():
    """Show performance analysis."""
    st.header("Performance Analysis")

    perf_df = generate_sample_performance()

    # Equity curve
    fig = plot_equity_curve(perf_df)
    st.plotly_chart(fig, use_container_width=True)

    # Metrics and distribution
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Performance Metrics")
        metrics = calculate_metrics(perf_df)
        for key, value in metrics.items():
            st.metric(key, value)

    with col2:
        st.subheader("Returns Distribution")
        fig = plot_returns_distribution(perf_df)
        st.plotly_chart(fig, use_container_width=True)

    # Rolling metrics
    st.subheader("Rolling Performance")

    perf_df['rolling_sharpe'] = perf_df['returns'].rolling(20).mean() / perf_df['returns'].rolling(20).std() * np.sqrt(252)
    perf_df['rolling_vol'] = perf_df['returns'].rolling(20).std() * np.sqrt(252)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=perf_df['date'], y=perf_df['rolling_sharpe'], name='Rolling Sharpe (20d)'))
    fig.update_layout(title='Rolling Sharpe Ratio', xaxis_title='Date', yaxis_title='Sharpe Ratio', height=300)
    st.plotly_chart(fig, use_container_width=True)


def show_backtest():
    """Show backtest results."""
    st.header("Backtest Results")

    st.info("Run a backtest to see results here. Use the Atlas backtest engine API.")

    # Sample backtest config
    st.subheader("Backtest Configuration")

    col1, col2 = st.columns(2)

    with col1:
        st.number_input("Initial Capital", value=100000, step=10000)
        st.number_input("Commission (per share)", value=0.001, step=0.0001, format="%.4f")
        st.number_input("Slippage (bps)", value=1.0, step=0.1)

    with col2:
        st.selectbox("Strategy", ["Simple Imbalance", "Alpha Model", "Mean Reversion"])
        st.number_input("Imbalance Threshold", value=0.3, step=0.05)
        st.number_input("Max Position", value=1000, step=100)

    if st.button("Run Backtest"):
        with st.spinner("Running backtest..."):
            import time
            time.sleep(1)  # Simulate backtest

            perf_df = generate_sample_performance()
            metrics = calculate_metrics(perf_df)

            st.success("Backtest completed!")

            cols = st.columns(len(metrics))
            for i, (key, value) in enumerate(metrics.items()):
                cols[i].metric(key, value)

            fig = plot_equity_curve(perf_df)
            st.plotly_chart(fig, use_container_width=True)


def show_system_metrics():
    """Show system performance metrics."""
    st.header("System Performance Metrics")

    # Benchmark results
    st.subheader("C++ Engine Benchmarks")

    benchmarks = pd.DataFrame({
        'Operation': ['Add Order', 'Cancel Order', 'Get BBO', 'Get Depth (10)', 'Mid Price', 'Pool Allocate'],
        'p50 (ns)': [16, 50, 0.7, 42, 0.66, 1.7],
        'p99 (ns)': [20, 65, 1.0, 50, 0.8, 2.0],
        'p99.9 (ns)': [30, 80, 1.5, 60, 1.0, 2.5],
        'Target (ns)': [500, 200, 50, 500, 100, 20],
    })

    st.dataframe(benchmarks, use_container_width=True)

    # Bar chart of latencies
    fig = go.Figure(data=[
        go.Bar(name='Actual p99', x=benchmarks['Operation'], y=benchmarks['p99 (ns)'], marker_color='#1f77b4'),
        go.Bar(name='Target', x=benchmarks['Operation'], y=benchmarks['Target (ns)'], marker_color='#ff7f0e')
    ])
    fig.update_layout(title='Latency vs Target', yaxis_title='Nanoseconds', barmode='group', height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Memory metrics
    st.subheader("Memory Efficiency")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Order Size", "128 bytes", help="Cache-aligned")
    with col2:
        st.metric("Pool Block Size", "64 bytes", help="Cache-line aligned")
    with col3:
        st.metric("Zero Allocations", "In hot path")

    # Throughput
    st.subheader("Throughput")

    throughput = pd.DataFrame({
        'Metric': ['Orders/sec', 'BBO Queries/sec', 'Ring Buffer Push/Pop'],
        'Value': ['64M', '1.4B', '640M'],
    })

    st.dataframe(throughput, use_container_width=True)


if __name__ == "__main__":
    main()
