"""Atlas - Smart Trading Platform."""

import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import random

# =============================================================================
# PAGE CONFIG - Hide Streamlit elements
# =============================================================================
st.set_page_config(
    page_title="Atlas | Smart Trading",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================================================================
# COLORS
# =============================================================================
COLORS = {
    "bg": "#0d1117",
    "card": "#161b22",
    "border": "#30363d",
    "accent": "#ff6b00",
    "accent2": "#ff8c00",
    "green": "#00d4aa",
    "red": "#ff4757",
    "text": "#ffffff",
    "text2": "#8b949e",
    "text3": "#484f58",
}

# =============================================================================
# HIDE STREAMLIT ELEMENTS & CUSTOM CSS
# =============================================================================
st.markdown("""
<style>
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stToolbar"] {display: none;}
    [data-testid="stDecoration"] {display: none;}
    [data-testid="stStatusWidget"] {display: none;}
    .viewerBadge_link__qRIco {display: none;}

    /* Hide sidebar toggle */
    [data-testid="collapsedControl"] {display: none;}

    /* Main styling */
    .stApp {
        background: #0d1117;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Remove padding */
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }

    /* Radio buttons as tabs */
    .stRadio > div {
        display: flex;
        gap: 0;
        background: #161b22;
        border-radius: 8px;
        padding: 4px;
    }
    .stRadio > div > label {
        background: transparent;
        padding: 10px 24px;
        border-radius: 6px;
        color: #8b949e;
        cursor: pointer;
        transition: all 0.2s;
        margin: 0;
    }
    .stRadio > div > label:hover {
        color: #ffffff;
    }
    .stRadio > div > label[data-checked="true"] {
        background: #ff6b00;
        color: #000000;
    }

    /* Hide radio circles */
    .stRadio > div > label > div:first-child {
        display: none;
    }

    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.9rem;
    }

    /* Card styling */
    .card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 24px;
    }

    /* Plotly chart background */
    .js-plotly-plot .plotly .bg {
        fill: #161b22 !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA SIMULATOR
# =============================================================================
@st.cache_data(ttl=2)
def get_market_data():
    """Generate simulated market data."""
    np.random.seed(int(datetime.now().timestamp()) % 1000)

    base_price = 87500 + np.random.uniform(-500, 500)

    # OHLC data
    dates = pd.date_range(end=datetime.now(), periods=100, freq='1h')
    prices = [base_price]
    for _ in range(99):
        change = np.random.normal(0, 100)
        prices.append(prices[-1] + change)

    ohlc = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p + abs(np.random.normal(0, 50)) for p in prices],
        'low': [p - abs(np.random.normal(0, 50)) for p in prices],
        'close': [p + np.random.normal(0, 30) for p in prices],
        'volume': [np.random.uniform(100, 1000) for _ in prices],
    })

    # Order book
    mid = ohlc['close'].iloc[-1]
    spread = np.random.uniform(5, 15)

    bid_prices = [mid - spread/2 - i * np.random.uniform(2, 5) for i in range(10)]
    ask_prices = [mid + spread/2 + i * np.random.uniform(2, 5) for i in range(10)]
    bid_sizes = [np.random.uniform(0.1, 3) for _ in range(10)]
    ask_sizes = [np.random.uniform(0.1, 3) for _ in range(10)]

    # Portfolio performance
    equity_dates = pd.date_range(end=datetime.now(), periods=90, freq='1D')
    equity = [100000]
    for _ in range(89):
        ret = np.random.normal(0.001, 0.015)
        equity.append(equity[-1] * (1 + ret))

    peak = np.maximum.accumulate(equity)
    drawdown = (np.array(equity) - peak) / peak

    return {
        'ohlc': ohlc,
        'mid': mid,
        'spread': spread,
        'bid_prices': bid_prices,
        'ask_prices': ask_prices,
        'bid_sizes': bid_sizes,
        'ask_sizes': ask_sizes,
        'equity': equity,
        'equity_dates': equity_dates,
        'drawdown': drawdown,
        'change_24h': np.random.uniform(-3, 5),
    }

# =============================================================================
# CHARTS
# =============================================================================
def create_price_chart(data):
    """Create candlestick chart."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25],
                        vertical_spacing=0.02)

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=data['ohlc']['date'],
        open=data['ohlc']['open'],
        high=data['ohlc']['high'],
        low=data['ohlc']['low'],
        close=data['ohlc']['close'],
        increasing=dict(line=dict(color=COLORS['green']), fillcolor=COLORS['green']),
        decreasing=dict(line=dict(color=COLORS['red']), fillcolor=COLORS['red']),
        name='Price'
    ), row=1, col=1)

    # Volume
    colors = [COLORS['green'] if c >= o else COLORS['red']
              for o, c in zip(data['ohlc']['open'], data['ohlc']['close'])]
    fig.add_trace(go.Bar(
        x=data['ohlc']['date'],
        y=data['ohlc']['volume'],
        marker_color=colors,
        opacity=0.5,
        name='Volume'
    ), row=2, col=1)

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        xaxis_rangeslider_visible=False,
        height=400,
    )

    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False)

    return fig


def create_depth_chart(data):
    """Create market depth chart."""
    fig = go.Figure()

    # Cumulative sizes
    bid_cum = np.cumsum(data['bid_sizes'])
    ask_cum = np.cumsum(data['ask_sizes'])

    fig.add_trace(go.Scatter(
        x=data['bid_prices'], y=bid_cum,
        fill='tozeroy', fillcolor='rgba(0, 212, 170, 0.2)',
        line=dict(color=COLORS['green'], width=2),
        name='Buyers'
    ))

    fig.add_trace(go.Scatter(
        x=data['ask_prices'], y=ask_cum,
        fill='tozeroy', fillcolor='rgba(255, 71, 87, 0.2)',
        line=dict(color=COLORS['red'], width=2),
        name='Sellers'
    ))

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(orientation='h', y=1.02, x=0.5, xanchor='center'),
        height=250,
        xaxis_title='Price ($)',
        yaxis_title='Quantity (BTC)',
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')

    return fig


def create_portfolio_chart(data):
    """Create portfolio value chart."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data['equity_dates'],
        y=data['equity'],
        fill='tozeroy',
        fillcolor='rgba(255, 107, 0, 0.1)',
        line=dict(color=COLORS['accent'], width=2),
        name='Portfolio Value'
    ))

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        height=300,
        yaxis_title='Value ($)',
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')

    return fig

# =============================================================================
# COMPONENTS
# =============================================================================
def render_navbar():
    """Render top navigation bar."""
    st.markdown(f"""
    <div style="background: {COLORS['card']}; border-bottom: 1px solid {COLORS['border']}; padding: 16px 32px; display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 32px;">
            <div style="font-size: 1.5rem; font-weight: 700; color: {COLORS['accent']};">
                📈 Atlas
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 24px;">
            <div style="color: {COLORS['text2']}; font-size: 0.9rem;">
                🟢 Markets Open
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_trading_panel(data):
    """Render trading panel."""
    change_color = COLORS['green'] if data['change_24h'] >= 0 else COLORS['red']

    html = f"""
    <html>
    <head>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Inter', sans-serif;
                background: {COLORS['card']};
                color: {COLORS['text']};
                padding: 24px;
                border-radius: 16px;
                border: 1px solid {COLORS['border']};
            }}
            .price-section {{
                text-align: center;
                padding: 20px;
                background: rgba(255,107,0,0.05);
                border-radius: 12px;
                margin-bottom: 24px;
            }}
            .pair {{ color: {COLORS['text2']}; font-size: 0.9rem; margin-bottom: 8px; }}
            .price {{ font-size: 2.2rem; font-weight: 700; margin-bottom: 4px; }}
            .change {{ font-size: 1rem; font-weight: 600; color: {change_color}; }}
            .tabs {{ display: flex; gap: 8px; margin-bottom: 20px; }}
            .tab {{
                flex: 1;
                padding: 14px;
                border: none;
                border-radius: 10px;
                font-weight: 600;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .tab.buy {{ background: {COLORS['green']}; color: #000; }}
            .tab.sell {{ background: {COLORS['border']}; color: {COLORS['text2']}; }}
            .tab:hover {{ transform: scale(1.02); }}
            .input-group {{ margin-bottom: 16px; }}
            .input-label {{ color: {COLORS['text2']}; font-size: 0.85rem; margin-bottom: 8px; display: block; }}
            .input {{
                width: 100%;
                padding: 14px;
                background: {COLORS['bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                color: {COLORS['text']};
                font-size: 1rem;
            }}
            .quick-amounts {{ display: flex; gap: 8px; margin-bottom: 20px; }}
            .quick-btn {{
                flex: 1;
                padding: 10px;
                background: transparent;
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text2']};
                font-size: 0.85rem;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .quick-btn:hover {{ border-color: {COLORS['accent']}; color: {COLORS['accent']}; }}
            .summary {{ padding: 16px; background: {COLORS['bg']}; border-radius: 10px; margin-bottom: 20px; }}
            .summary-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.9rem; }}
            .summary-row:last-child {{ margin-bottom: 0; }}
            .summary-label {{ color: {COLORS['text2']}; }}
            .summary-value {{ color: {COLORS['text']}; font-weight: 500; }}
            .submit-btn {{
                width: 100%;
                padding: 16px;
                background: linear-gradient(135deg, {COLORS['green']}, #00b894);
                border: none;
                border-radius: 12px;
                color: #000;
                font-weight: 700;
                font-size: 1.1rem;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .submit-btn:hover {{ transform: scale(1.02); box-shadow: 0 4px 20px rgba(0,212,170,0.3); }}
        </style>
    </head>
    <body>
        <div class="price-section">
            <div class="pair">Bitcoin / US Dollar</div>
            <div class="price">${data['mid']:,.2f}</div>
            <div class="change">{data['change_24h']:+.2f}% today</div>
        </div>

        <div class="tabs">
            <button class="tab buy">Buy</button>
            <button class="tab sell">Sell</button>
        </div>

        <div class="input-group">
            <label class="input-label">Amount in USD</label>
            <input type="text" class="input" value="1,000.00" />
        </div>

        <div class="quick-amounts">
            <button class="quick-btn">$100</button>
            <button class="quick-btn">$500</button>
            <button class="quick-btn">$1K</button>
            <button class="quick-btn">$5K</button>
        </div>

        <div class="summary">
            <div class="summary-row">
                <span class="summary-label">You'll receive</span>
                <span class="summary-value">≈ 0.0114 BTC</span>
            </div>
            <div class="summary-row">
                <span class="summary-label">Fee (0.1%)</span>
                <span class="summary-value">$1.00</span>
            </div>
        </div>

        <button class="submit-btn">Buy Bitcoin</button>
    </body>
    </html>
    """
    components.html(html, height=580)


def render_order_book(data):
    """Render order book."""
    max_size = max(max(data['ask_sizes']), max(data['bid_sizes']))

    ask_rows = ""
    for i in range(5, -1, -1):
        depth = (data['ask_sizes'][i] / max_size) * 100
        ask_rows += f"""
        <div class="row" style="--depth: {depth}%;">
            <span class="price sell">${data['ask_prices'][i]:,.2f}</span>
            <span class="size">{data['ask_sizes'][i]:.4f}</span>
            <span class="total">${data['ask_sizes'][i] * data['ask_prices'][i]:,.0f}</span>
            <div class="depth-bar sell"></div>
        </div>
        """

    bid_rows = ""
    for i in range(6):
        depth = (data['bid_sizes'][i] / max_size) * 100
        bid_rows += f"""
        <div class="row" style="--depth: {depth}%;">
            <span class="price buy">${data['bid_prices'][i]:,.2f}</span>
            <span class="size">{data['bid_sizes'][i]:.4f}</span>
            <span class="total">${data['bid_sizes'][i] * data['bid_prices'][i]:,.0f}</span>
            <div class="depth-bar buy"></div>
        </div>
        """

    html = f"""
    <html>
    <head>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Inter', sans-serif;
                background: {COLORS['card']};
                color: {COLORS['text']};
                border-radius: 16px;
                border: 1px solid {COLORS['border']};
                overflow: hidden;
            }}
            .header {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                padding: 16px 20px;
                background: {COLORS['bg']};
                font-size: 0.75rem;
                font-weight: 600;
                color: {COLORS['text3']};
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .header span:nth-child(2) {{ text-align: center; }}
            .header span:nth-child(3) {{ text-align: right; }}
            .row {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                padding: 12px 20px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.9rem;
                position: relative;
            }}
            .row:hover {{ background: rgba(255,255,255,0.03); }}
            .depth-bar {{
                position: absolute;
                top: 0;
                height: 100%;
                width: var(--depth);
                opacity: 0.1;
            }}
            .depth-bar.sell {{ right: 0; background: {COLORS['red']}; }}
            .depth-bar.buy {{ left: 0; background: {COLORS['green']}; }}
            .price {{ position: relative; z-index: 1; font-weight: 500; }}
            .price.sell {{ color: {COLORS['red']}; }}
            .price.buy {{ color: {COLORS['green']}; }}
            .size {{ text-align: center; position: relative; z-index: 1; }}
            .total {{ text-align: right; color: {COLORS['text2']}; position: relative; z-index: 1; }}
            .spread {{
                padding: 12px 20px;
                text-align: center;
                background: {COLORS['bg']};
                color: {COLORS['accent']};
                font-weight: 600;
                font-size: 0.9rem;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <span>Price</span>
            <span>Amount</span>
            <span>Total</span>
        </div>
        {ask_rows}
        <div class="spread">Spread: ${data['spread']:.2f}</div>
        {bid_rows}
    </body>
    </html>
    """
    components.html(html, height=450)


def render_stats_card(label, value, change=None, prefix=""):
    """Render a stats card."""
    change_html = ""
    if change is not None:
        color = COLORS['green'] if change >= 0 else COLORS['red']
        change_html = f'<div style="color: {color}; font-size: 0.9rem; font-weight: 500;">{change:+.2f}%</div>'

    st.markdown(f"""
    <div style="background: {COLORS['card']}; border: 1px solid {COLORS['border']}; border-radius: 12px; padding: 20px;">
        <div style="color: {COLORS['text2']}; font-size: 0.85rem; margin-bottom: 8px;">{label}</div>
        <div style="font-size: 1.5rem; font-weight: 700; color: {COLORS['text']};">{prefix}{value}</div>
        {change_html}
    </div>
    """, unsafe_allow_html=True)


def render_footer():
    """Render footer."""
    st.markdown(f"""
    <div style="background: {COLORS['card']}; border-top: 1px solid {COLORS['border']}; padding: 32px; margin-top: 48px;">
        <div style="max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 24px;">
            <div>
                <div style="font-size: 1.2rem; font-weight: 700; color: {COLORS['accent']}; margin-bottom: 8px;">📈 Atlas</div>
                <div style="color: {COLORS['text2']}; font-size: 0.85rem;">Smart trading for everyone</div>
            </div>
            <div style="display: flex; gap: 32px;">
                <a href="#" style="color: {COLORS['text2']}; text-decoration: none; font-size: 0.9rem;">About</a>
                <a href="#" style="color: {COLORS['text2']}; text-decoration: none; font-size: 0.9rem;">Help</a>
                <a href="#" style="color: {COLORS['text2']}; text-decoration: none; font-size: 0.9rem;">Terms</a>
                <a href="#" style="color: {COLORS['text2']}; text-decoration: none; font-size: 0.9rem;">Privacy</a>
            </div>
            <div style="color: {COLORS['text3']}; font-size: 0.8rem;">
                © 2024 Atlas. All rights reserved.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# PAGES
# =============================================================================
def page_trade(data):
    """Trading page."""
    st.markdown("<div style='padding: 32px;'>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1], gap="large")

    with col1:
        st.markdown(f"""
        <div style="margin-bottom: 16px;">
            <span style="font-size: 1.5rem; font-weight: 700; color: {COLORS['text']};">Bitcoin</span>
            <span style="color: {COLORS['text2']}; margin-left: 8px;">BTC/USD</span>
        </div>
        """, unsafe_allow_html=True)

        fig = create_price_chart(data)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

        st.markdown(f"<div style='font-size: 1.1rem; font-weight: 600; color: {COLORS['text']}; margin-bottom: 16px;'>Market Depth</div>", unsafe_allow_html=True)
        fig = create_depth_chart(data)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with col2:
        render_trading_panel(data)

    st.markdown("</div>", unsafe_allow_html=True)


def page_market(data):
    """Market overview page."""
    st.markdown("<div style='padding: 32px;'>", unsafe_allow_html=True)

    st.markdown(f"<div style='font-size: 1.5rem; font-weight: 700; color: {COLORS['text']}; margin-bottom: 24px;'>Live Order Book</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1.5, 1], gap="large")

    with col1:
        render_order_book(data)

    with col2:
        st.markdown(f"<div style='font-size: 1.1rem; font-weight: 600; color: {COLORS['text']}; margin-bottom: 16px;'>Market Activity</div>", unsafe_allow_html=True)
        fig = create_depth_chart(data)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        st.markdown(f"""
        <div style="background: {COLORS['card']}; border: 1px solid {COLORS['border']}; border-radius: 12px; padding: 20px; margin-top: 16px;">
            <div style="font-size: 1rem; font-weight: 600; color: {COLORS['text']}; margin-bottom: 16px;">Quick Stats</div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                <span style="color: {COLORS['text2']};">24h Volume</span>
                <span style="color: {COLORS['text']}; font-weight: 500;">$2.4B</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                <span style="color: {COLORS['text2']};">24h High</span>
                <span style="color: {COLORS['green']}; font-weight: 500;">${data['mid'] + 1200:,.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: {COLORS['text2']};">24h Low</span>
                <span style="color: {COLORS['red']}; font-weight: 500;">${data['mid'] - 800:,.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def page_portfolio(data):
    """Portfolio page."""
    st.markdown("<div style='padding: 32px;'>", unsafe_allow_html=True)

    st.markdown(f"<div style='font-size: 1.5rem; font-weight: 700; color: {COLORS['text']}; margin-bottom: 24px;'>Your Portfolio</div>", unsafe_allow_html=True)

    # Stats
    total_value = data['equity'][-1]
    total_return = (total_value / data['equity'][0] - 1) * 100

    cols = st.columns(4)
    with cols[0]:
        render_stats_card("Total Value", f"{total_value:,.0f}", prefix="$")
    with cols[1]:
        render_stats_card("Total Return", f"{total_return:.1f}%", change=total_return)
    with cols[2]:
        render_stats_card("Today's Gain", f"{total_value * 0.012:,.0f}", change=1.2, prefix="$")
    with cols[3]:
        render_stats_card("Best Asset", "BTC", change=5.2)

    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    # Chart
    st.markdown(f"<div style='font-size: 1.1rem; font-weight: 600; color: {COLORS['text']}; margin-bottom: 16px;'>Value Over Time</div>", unsafe_allow_html=True)
    fig = create_portfolio_chart(data)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Holdings
    st.markdown(f"<div style='font-size: 1.1rem; font-weight: 600; color: {COLORS['text']}; margin: 24px 0 16px;'>Your Holdings</div>", unsafe_allow_html=True)

    holdings_html = f"""
    <div style="background: {COLORS['card']}; border: 1px solid {COLORS['border']}; border-radius: 12px; overflow: hidden;">
        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; padding: 16px 24px; background: {COLORS['bg']}; font-size: 0.8rem; color: {COLORS['text3']}; text-transform: uppercase; font-weight: 600;">
            <span>Asset</span>
            <span style="text-align: right;">Amount</span>
            <span style="text-align: right;">Value</span>
            <span style="text-align: right;">Change</span>
        </div>
        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; padding: 20px 24px; border-top: 1px solid {COLORS['border']}; align-items: center;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 40px; height: 40px; background: #f7931a; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold;">₿</div>
                <div>
                    <div style="font-weight: 600; color: {COLORS['text']};">Bitcoin</div>
                    <div style="font-size: 0.85rem; color: {COLORS['text2']};">BTC</div>
                </div>
            </div>
            <div style="text-align: right; color: {COLORS['text']};">1.2453</div>
            <div style="text-align: right; color: {COLORS['text']}; font-weight: 600;">$109,012</div>
            <div style="text-align: right; color: {COLORS['green']}; font-weight: 500;">+5.2%</div>
        </div>
        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; padding: 20px 24px; border-top: 1px solid {COLORS['border']}; align-items: center;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 40px; height: 40px; background: #627eea; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold;">Ξ</div>
                <div>
                    <div style="font-weight: 600; color: {COLORS['text']};">Ethereum</div>
                    <div style="font-size: 0.85rem; color: {COLORS['text2']};">ETH</div>
                </div>
            </div>
            <div style="text-align: right; color: {COLORS['text']};">8.5000</div>
            <div style="text-align: right; color: {COLORS['text']}; font-weight: 600;">$28,450</div>
            <div style="text-align: right; color: {COLORS['red']}; font-weight: 500;">-1.3%</div>
        </div>
    </div>
    """
    st.markdown(holdings_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# MAIN
# =============================================================================
def main():
    # Get data
    data = get_market_data()

    # Navbar
    render_navbar()

    # Navigation tabs
    st.markdown("<div style='padding: 24px 32px 0;'>", unsafe_allow_html=True)

    cols = st.columns([1, 3])
    with cols[0]:
        page = st.radio(
            "nav",
            ["Trade", "Markets", "Portfolio"],
            horizontal=True,
            label_visibility="collapsed"
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # Page content
    if page == "Trade":
        page_trade(data)
    elif page == "Markets":
        page_market(data)
    elif page == "Portfolio":
        page_portfolio(data)

    # Footer
    render_footer()


if __name__ == "__main__":
    main()
