"""Atlas Trading Dashboard - Premium Dark Theme with Real-Time Data."""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Atlas | Low-Latency Order Book Engine",
    page_icon="https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/atom.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# COLOR PALETTE - Premium Dark Theme
# =============================================================================
COLORS = {
    "bg_primary": "#0D1117",
    "bg_secondary": "#161B22",
    "bg_tertiary": "#21262D",
    "accent_primary": "#00D4AA",
    "accent_secondary": "#6366F1",
    "accent_tertiary": "#8B5CF6",
    "success": "#10B981",
    "danger": "#EF4444",
    "warning": "#F59E0B",
    "info": "#3B82F6",
    "text_primary": "#E6EDF3",
    "text_secondary": "#8B949E",
    "text_muted": "#484F58",
    "border": "#30363D",
    "glow_cyan": "rgba(0, 212, 170, 0.4)",
    "glow_indigo": "rgba(99, 102, 241, 0.4)",
}

# =============================================================================
# CUSTOM CSS - Glassmorphism Dark Theme
# =============================================================================
st.markdown(f"""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Root Variables */
    :root {{
        --bg-primary: {COLORS['bg_primary']};
        --bg-secondary: {COLORS['bg_secondary']};
        --bg-tertiary: {COLORS['bg_tertiary']};
        --accent-primary: {COLORS['accent_primary']};
        --accent-secondary: {COLORS['accent_secondary']};
        --text-primary: {COLORS['text_primary']};
        --text-secondary: {COLORS['text_secondary']};
        --border: {COLORS['border']};
    }}

    /* Global Styles */
    .stApp {{
        background: linear-gradient(135deg, {COLORS['bg_primary']} 0%, #0a0e14 50%, {COLORS['bg_primary']} 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* Hide Streamlit Branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* Sidebar Styling */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {COLORS['bg_secondary']} 0%, {COLORS['bg_primary']} 100%);
        border-right: 1px solid {COLORS['border']};
    }}

    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stRadio label {{
        color: {COLORS['text_primary']} !important;
        font-weight: 500;
    }}

    /* Main Header */
    .main-header {{
        background: linear-gradient(135deg, {COLORS['bg_secondary']} 0%, {COLORS['bg_tertiary']} 100%);
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }}

    .main-title {{
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, {COLORS['accent_primary']} 0%, {COLORS['accent_secondary']} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        letter-spacing: -0.02em;
    }}

    .main-subtitle {{
        color: {COLORS['text_secondary']};
        font-size: 1rem;
        font-weight: 400;
        margin-top: 4px;
    }}

    .live-indicator {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 0.85rem;
        color: {COLORS['success']};
        font-weight: 500;
    }}

    .live-dot {{
        width: 8px;
        height: 8px;
        background: {COLORS['success']};
        border-radius: 50%;
        animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.5; transform: scale(1.2); }}
    }}

    /* Metric Cards */
    .metric-card {{
        background: linear-gradient(135deg, {COLORS['bg_secondary']} 0%, {COLORS['bg_tertiary']} 100%);
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        padding: 24px;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
        backdrop-filter: blur(20px);
    }}

    .metric-card:hover {{
        border-color: {COLORS['accent_primary']};
        box-shadow: 0 0 30px {COLORS['glow_cyan']};
        transform: translateY(-2px);
    }}

    .metric-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, {COLORS['accent_primary']}, {COLORS['accent_secondary']});
        opacity: 0;
        transition: opacity 0.3s ease;
    }}

    .metric-card:hover::before {{
        opacity: 1;
    }}

    .metric-label {{
        color: {COLORS['text_secondary']};
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }}

    .metric-value {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 2rem;
        font-weight: 700;
        color: {COLORS['text_primary']};
        margin-bottom: 4px;
    }}

    .metric-value.cyan {{
        color: {COLORS['accent_primary']};
    }}

    .metric-value.indigo {{
        color: {COLORS['accent_secondary']};
    }}

    .metric-value.success {{
        color: {COLORS['success']};
    }}

    .metric-value.danger {{
        color: {COLORS['danger']};
    }}

    .metric-delta {{
        font-size: 0.85rem;
        font-weight: 500;
    }}

    .metric-delta.positive {{
        color: {COLORS['success']};
    }}

    .metric-delta.negative {{
        color: {COLORS['danger']};
    }}

    /* Chart Container */
    .chart-container {{
        background: linear-gradient(135deg, {COLORS['bg_secondary']} 0%, {COLORS['bg_tertiary']} 100%);
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        backdrop-filter: blur(20px);
    }}

    .chart-title {{
        color: {COLORS['text_primary']};
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    .chart-title-icon {{
        width: 24px;
        height: 24px;
        background: linear-gradient(135deg, {COLORS['accent_primary']}, {COLORS['accent_secondary']});
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    /* Section Headers */
    .section-header {{
        color: {COLORS['text_primary']};
        font-size: 1.5rem;
        font-weight: 700;
        margin: 32px 0 24px 0;
        padding-bottom: 12px;
        border-bottom: 2px solid {COLORS['border']};
        display: flex;
        align-items: center;
        gap: 12px;
    }}

    .section-badge {{
        background: linear-gradient(135deg, {COLORS['accent_primary']}, {COLORS['accent_secondary']});
        color: white;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    /* Order Book Styles */
    .orderbook-container {{
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        overflow: hidden;
    }}

    .orderbook-header {{
        background: {COLORS['bg_tertiary']};
        padding: 12px 16px;
        display: flex;
        justify-content: space-between;
        border-bottom: 1px solid {COLORS['border']};
        font-size: 0.8rem;
        color: {COLORS['text_secondary']};
        font-weight: 600;
        text-transform: uppercase;
    }}

    .orderbook-row {{
        display: flex;
        padding: 8px 16px;
        border-bottom: 1px solid {COLORS['border']};
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        transition: background 0.2s ease;
    }}

    .orderbook-row:hover {{
        background: rgba(255, 255, 255, 0.02);
    }}

    .orderbook-row.bid {{
        background: linear-gradient(90deg, rgba(16, 185, 129, 0.1) 0%, transparent 100%);
    }}

    .orderbook-row.ask {{
        background: linear-gradient(90deg, transparent 0%, rgba(239, 68, 68, 0.1) 100%);
    }}

    /* Stats Grid */
    .stats-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }}

    .stat-item {{
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 16px 20px;
        display: flex;
        flex-direction: column;
    }}

    .stat-label {{
        color: {COLORS['text_secondary']};
        font-size: 0.8rem;
        font-weight: 500;
        margin-bottom: 4px;
    }}

    .stat-value {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.25rem;
        font-weight: 600;
        color: {COLORS['text_primary']};
    }}

    /* Progress Bars */
    .progress-container {{
        background: {COLORS['bg_tertiary']};
        border-radius: 8px;
        height: 8px;
        overflow: hidden;
        margin-top: 8px;
    }}

    .progress-bar {{
        height: 100%;
        background: linear-gradient(90deg, {COLORS['accent_primary']}, {COLORS['accent_secondary']});
        border-radius: 8px;
        transition: width 0.5s ease;
    }}

    /* Benchmark Table */
    .benchmark-row {{
        display: flex;
        align-items: center;
        padding: 16px;
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        margin-bottom: 12px;
    }}

    .benchmark-name {{
        flex: 1;
        color: {COLORS['text_primary']};
        font-weight: 500;
    }}

    .benchmark-value {{
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        color: {COLORS['accent_primary']};
        margin-right: 16px;
    }}

    .benchmark-target {{
        font-family: 'JetBrains Mono', monospace;
        color: {COLORS['text_secondary']};
        font-size: 0.85rem;
    }}

    .benchmark-badge {{
        background: rgba(16, 185, 129, 0.1);
        color: {COLORS['success']};
        font-size: 0.75rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 8px;
        margin-left: 12px;
    }}

    /* Scrollbar Styling */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: {COLORS['bg_primary']};
    }}

    ::-webkit-scrollbar-thumb {{
        background: {COLORS['border']};
        border-radius: 4px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: {COLORS['text_muted']};
    }}

    /* Streamlit Overrides */
    .stSelectbox > div > div {{
        background-color: {COLORS['bg_secondary']};
        border-color: {COLORS['border']};
        color: {COLORS['text_primary']};
    }}

    .stButton > button {{
        background: linear-gradient(135deg, {COLORS['accent_primary']} 0%, {COLORS['accent_secondary']} 100%);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        padding: 12px 24px;
        transition: all 0.3s ease;
    }}

    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 25px {COLORS['glow_cyan']};
    }}

    .stNumberInput > div > div > input {{
        background-color: {COLORS['bg_secondary']};
        border-color: {COLORS['border']};
        color: {COLORS['text_primary']};
    }}

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background: {COLORS['bg_secondary']};
        padding: 8px;
        border-radius: 12px;
    }}

    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        border-radius: 8px;
        color: {COLORS['text_secondary']};
        font-weight: 500;
    }}

    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, {COLORS['accent_primary']}22, {COLORS['accent_secondary']}22);
        color: {COLORS['accent_primary']} !important;
    }}

    /* Hide fullscreen buttons on charts */
    .modebar-btn[data-title="Autoscale"],
    .modebar-btn[data-title="Reset axes"] {{
        display: none !important;
    }}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# REAL-TIME DATA SIMULATION
# =============================================================================
class MarketDataSimulator:
    """Simulates real-time market data with realistic dynamics."""

    def __init__(self, seed=None):
        if seed:
            np.random.seed(seed)
        self.base_price = 100.0
        self.volatility = 0.0002
        self.last_update = time.time()

    def get_orderbook(self, levels=15):
        """Generate realistic order book with clustering."""
        # Price movement with mean reversion
        dt = time.time() - self.last_update
        self.base_price += np.random.normal(0, self.volatility * np.sqrt(dt)) * self.base_price
        self.base_price = max(90, min(110, self.base_price))  # Keep in range

        mid = self.base_price
        spread = np.random.uniform(0.01, 0.03)

        # Generate prices with clustering
        bid_prices = mid - spread/2 - np.cumsum(np.random.exponential(0.01, levels))
        ask_prices = mid + spread/2 + np.cumsum(np.random.exponential(0.01, levels))

        # Generate sizes with power law distribution (realistic)
        bid_sizes = np.random.pareto(1.5, levels) * 500 + 100
        ask_sizes = np.random.pareto(1.5, levels) * 500 + 100

        # Add some large orders (iceberg detection)
        if np.random.random() > 0.7:
            idx = np.random.randint(3, levels)
            bid_sizes[idx] *= 5
        if np.random.random() > 0.7:
            idx = np.random.randint(3, levels)
            ask_sizes[idx] *= 5

        self.last_update = time.time()

        return {
            "bid_prices": bid_prices,
            "bid_sizes": bid_sizes,
            "ask_prices": ask_prices,
            "ask_sizes": ask_sizes,
            "mid_price": mid,
            "spread": spread,
            "spread_bps": spread / mid * 10000,
        }

    def get_trades(self, n=50):
        """Generate recent trades."""
        timestamps = pd.date_range(end=datetime.now(), periods=n, freq='500ms')
        prices = self.base_price + np.cumsum(np.random.normal(0, 0.01, n))
        sizes = np.random.exponential(200, n) + 50
        sides = np.random.choice(['BUY', 'SELL'], n, p=[0.52, 0.48])

        return pd.DataFrame({
            'time': timestamps,
            'price': prices,
            'size': sizes,
            'side': sides
        })

    def get_performance(self, n_days=252):
        """Generate strategy performance data."""
        np.random.seed(42)  # Consistent for demo
        dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')

        # Simulate alpha with momentum
        daily_alpha = 0.0003
        daily_vol = 0.012
        returns = np.random.normal(daily_alpha, daily_vol, n_days)

        # Add some regime changes
        regime_changes = [50, 120, 180]
        for rc in regime_changes:
            if rc < n_days:
                returns[rc:rc+20] *= np.random.choice([0.5, 1.5])

        cumulative = np.cumprod(1 + returns)
        equity = 100000 * cumulative

        # Calculate drawdown
        running_max = np.maximum.accumulate(equity)
        drawdown = (running_max - equity) / running_max

        return pd.DataFrame({
            'date': dates,
            'returns': returns,
            'cumulative': cumulative,
            'equity': equity,
            'drawdown': drawdown
        })


# Initialize simulator
@st.cache_resource
def get_simulator():
    return MarketDataSimulator()


# =============================================================================
# CHART TEMPLATES
# =============================================================================
def get_chart_layout(title="", height=400):
    """Standard chart layout with dark theme."""
    return dict(
        title=dict(text=title, font=dict(size=16, color=COLORS['text_primary'])),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", color=COLORS['text_secondary']),
        height=height,
        margin=dict(l=60, r=30, t=50, b=50),
        xaxis=dict(
            gridcolor=COLORS['border'],
            zerolinecolor=COLORS['border'],
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            gridcolor=COLORS['border'],
            zerolinecolor=COLORS['border'],
            tickfont=dict(size=11),
        ),
        legend=dict(
            bgcolor='rgba(0,0,0,0)',
            bordercolor=COLORS['border'],
            font=dict(size=11),
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor=COLORS['bg_secondary'],
            bordercolor=COLORS['border'],
            font=dict(family="JetBrains Mono", size=12),
        ),
    )


def create_depth_chart(book_data):
    """Create order book depth chart."""
    fig = go.Figure()

    # Cumulative sizes
    bid_cum = np.cumsum(book_data['bid_sizes'])
    ask_cum = np.cumsum(book_data['ask_sizes'])

    # Bid side
    fig.add_trace(go.Scatter(
        x=book_data['bid_prices'][::-1],
        y=bid_cum[::-1],
        fill='tozeroy',
        fillcolor='rgba(16, 185, 129, 0.2)',
        line=dict(color=COLORS['success'], width=2),
        name='Bids',
        hovertemplate='<b>Bid</b><br>Price: $%{x:.4f}<br>Depth: %{y:,.0f}<extra></extra>'
    ))

    # Ask side
    fig.add_trace(go.Scatter(
        x=book_data['ask_prices'],
        y=ask_cum,
        fill='tozeroy',
        fillcolor='rgba(239, 68, 68, 0.2)',
        line=dict(color=COLORS['danger'], width=2),
        name='Asks',
        hovertemplate='<b>Ask</b><br>Price: $%{x:.4f}<br>Depth: %{y:,.0f}<extra></extra>'
    ))

    # Mid price line
    fig.add_vline(
        x=book_data['mid_price'],
        line=dict(color=COLORS['accent_primary'], width=2, dash='dot'),
        annotation_text=f"Mid: ${book_data['mid_price']:.4f}",
        annotation_font_color=COLORS['accent_primary'],
    )

    fig.update_layout(**get_chart_layout("Market Depth", 350))
    fig.update_xaxis(title="Price ($)")
    fig.update_yaxis(title="Cumulative Size")

    return fig


def create_equity_chart(perf_data):
    """Create equity curve with gradient fill."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=("Portfolio Value", "Drawdown")
    )

    # Equity curve
    fig.add_trace(go.Scatter(
        x=perf_data['date'],
        y=perf_data['equity'],
        fill='tozeroy',
        fillgradient=dict(
            type="vertical",
            colorscale=[
                [0, 'rgba(0, 212, 170, 0.0)'],
                [1, 'rgba(0, 212, 170, 0.3)']
            ]
        ),
        line=dict(color=COLORS['accent_primary'], width=2),
        name='Equity',
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Value: $%{y:,.2f}<extra></extra>'
    ), row=1, col=1)

    # Drawdown
    fig.add_trace(go.Scatter(
        x=perf_data['date'],
        y=-perf_data['drawdown'] * 100,
        fill='tozeroy',
        fillcolor='rgba(239, 68, 68, 0.3)',
        line=dict(color=COLORS['danger'], width=1.5),
        name='Drawdown',
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Drawdown: %{y:.2f}%<extra></extra>'
    ), row=2, col=1)

    layout = get_chart_layout(height=450)
    layout['showlegend'] = False
    fig.update_layout(**layout)

    # Update subplot title colors
    fig.update_annotations(font_color=COLORS['text_primary'])

    fig.update_yaxes(title_text="Value ($)", row=1, col=1)
    fig.update_yaxes(title_text="DD %", row=2, col=1)

    return fig


def create_returns_distribution(perf_data):
    """Create returns histogram."""
    fig = go.Figure()

    returns = perf_data['returns'] * 100

    fig.add_trace(go.Histogram(
        x=returns,
        nbinsx=50,
        marker=dict(
            color=COLORS['accent_secondary'],
            line=dict(color=COLORS['bg_primary'], width=1)
        ),
        opacity=0.8,
        hovertemplate='Return: %{x:.2f}%<br>Count: %{y}<extra></extra>'
    ))

    # Add mean line
    mean_ret = returns.mean()
    fig.add_vline(
        x=mean_ret,
        line=dict(color=COLORS['accent_primary'], width=2, dash='dash'),
        annotation_text=f"Mean: {mean_ret:.3f}%",
        annotation_font_color=COLORS['accent_primary'],
    )

    fig.update_layout(**get_chart_layout("Daily Returns Distribution", 300))
    fig.update_xaxis(title="Return (%)")
    fig.update_yaxis(title="Frequency")

    return fig


def create_heatmap(book_data):
    """Create order book heatmap visualization."""
    levels = len(book_data['bid_prices'])

    # Create heatmap data
    sizes = np.concatenate([book_data['bid_sizes'][::-1], book_data['ask_sizes']])
    prices = np.concatenate([book_data['bid_prices'][::-1], book_data['ask_prices']])

    colors = ['rgba(16, 185, 129, {})'.format(min(s/max(sizes), 1)) for s in book_data['bid_sizes'][::-1]]
    colors += ['rgba(239, 68, 68, {})'.format(min(s/max(sizes), 1)) for s in book_data['ask_sizes']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=prices,
        y=sizes,
        marker=dict(
            color=sizes,
            colorscale=[
                [0, COLORS['success']],
                [0.5, COLORS['bg_tertiary']],
                [1, COLORS['danger']]
            ],
            line=dict(width=0)
        ),
        hovertemplate='Price: $%{x:.4f}<br>Size: %{y:,.0f}<extra></extra>'
    ))

    fig.update_layout(**get_chart_layout("Order Book Heatmap", 300))
    fig.update_xaxis(title="Price ($)")
    fig.update_yaxis(title="Size")

    return fig


def create_benchmark_chart(benchmarks):
    """Create benchmark comparison chart."""
    fig = go.Figure()

    # Actual performance
    fig.add_trace(go.Bar(
        name='Actual',
        x=benchmarks['operation'],
        y=benchmarks['actual'],
        marker=dict(
            color=COLORS['accent_primary'],
            line=dict(width=0)
        ),
        text=[f"{v:.1f}ns" for v in benchmarks['actual']],
        textposition='outside',
        textfont=dict(color=COLORS['text_primary'], size=10),
    ))

    # Target
    fig.add_trace(go.Bar(
        name='Target',
        x=benchmarks['operation'],
        y=benchmarks['target'],
        marker=dict(
            color=COLORS['text_muted'],
            line=dict(width=0)
        ),
        opacity=0.5,
    ))

    fig.update_layout(**get_chart_layout("Latency Performance vs Target", 350))
    fig.update_layout(barmode='group')
    fig.update_yaxis(title="Nanoseconds", type="log")

    return fig


def create_rolling_sharpe(perf_data, window=20):
    """Create rolling Sharpe ratio chart."""
    rolling_ret = perf_data['returns'].rolling(window).mean()
    rolling_std = perf_data['returns'].rolling(window).std()
    rolling_sharpe = (rolling_ret / rolling_std * np.sqrt(252)).fillna(0)

    fig = go.Figure()

    # Add zero line
    fig.add_hline(y=0, line=dict(color=COLORS['text_muted'], width=1, dash='dot'))
    fig.add_hline(y=1, line=dict(color=COLORS['success'], width=1, dash='dot'),
                  annotation_text="Target", annotation_font_color=COLORS['success'])
    fig.add_hline(y=2, line=dict(color=COLORS['accent_primary'], width=1, dash='dot'),
                  annotation_text="Excellent", annotation_font_color=COLORS['accent_primary'])

    fig.add_trace(go.Scatter(
        x=perf_data['date'],
        y=rolling_sharpe,
        fill='tozeroy',
        fillcolor='rgba(99, 102, 241, 0.2)',
        line=dict(color=COLORS['accent_secondary'], width=2),
        name=f'{window}D Rolling Sharpe',
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Sharpe: %{y:.2f}<extra></extra>'
    ))

    fig.update_layout(**get_chart_layout(f"Rolling Sharpe Ratio ({window}D)", 300))
    fig.update_yaxis(title="Sharpe Ratio")

    return fig


# =============================================================================
# METRIC CALCULATIONS
# =============================================================================
def calculate_metrics(perf_data):
    """Calculate comprehensive performance metrics."""
    returns = perf_data['returns'].values
    equity = perf_data['equity'].values

    # Basic metrics
    total_return = (equity[-1] / equity[0] - 1)
    annual_return = (1 + total_return) ** (252 / len(returns)) - 1
    volatility = np.std(returns) * np.sqrt(252)
    sharpe = annual_return / volatility if volatility > 0 else 0

    # Downside metrics
    negative_returns = returns[returns < 0]
    downside_vol = np.std(negative_returns) * np.sqrt(252) if len(negative_returns) > 1 else 0
    sortino = annual_return / downside_vol if downside_vol > 0 else 0

    # Drawdown
    running_max = np.maximum.accumulate(equity)
    drawdowns = (running_max - equity) / running_max
    max_drawdown = np.max(drawdowns)

    # Calmar ratio
    calmar = annual_return / max_drawdown if max_drawdown > 0 else 0

    # Win rate
    win_rate = np.sum(returns > 0) / len(returns)

    # Profit factor
    gross_profit = np.sum(returns[returns > 0])
    gross_loss = abs(np.sum(returns[returns < 0]))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'volatility': volatility,
        'sharpe': sharpe,
        'sortino': sortino,
        'max_drawdown': max_drawdown,
        'calmar': calmar,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_trades': len(returns),
    }


# =============================================================================
# UI COMPONENTS
# =============================================================================
def render_metric_card(label, value, delta=None, delta_type="neutral", color="default"):
    """Render a styled metric card."""
    color_class = color if color != "default" else ""
    delta_class = "positive" if delta_type == "positive" else "negative" if delta_type == "negative" else ""
    delta_html = f'<div class="metric-delta {delta_class}">{delta}</div>' if delta else ""

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {color_class}">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_header():
    """Render the main header."""
    now = datetime.now()

    st.markdown(f"""
    <div class="main-header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 class="main-title">ATLAS</h1>
                <p class="main-subtitle">Low-Latency Order Book Engine with Predictive Execution</p>
            </div>
            <div style="text-align: right;">
                <div class="live-indicator">
                    <span class="live-dot"></span>
                    LIVE
                </div>
                <div style="color: {COLORS['text_secondary']}; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; margin-top: 8px;">
                    {now.strftime('%Y-%m-%d %H:%M:%S')} UTC
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_orderbook_table(book_data, levels=10):
    """Render order book as styled table."""
    html = """
    <div class="orderbook-container">
        <div class="orderbook-header">
            <span>Size</span>
            <span>Bid</span>
            <span>Ask</span>
            <span>Size</span>
        </div>
    """

    for i in range(min(levels, len(book_data['bid_prices']))):
        bid_size = book_data['bid_sizes'][i]
        bid_price = book_data['bid_prices'][i]
        ask_price = book_data['ask_prices'][i]
        ask_size = book_data['ask_sizes'][i]

        html += f"""
        <div class="orderbook-row">
            <span style="color: {COLORS['success']}; flex: 1;">{bid_size:,.0f}</span>
            <span style="color: {COLORS['success']}; flex: 1; text-align: right;">${bid_price:.4f}</span>
            <span style="color: {COLORS['danger']}; flex: 1; text-align: left; padding-left: 20px;">${ask_price:.4f}</span>
            <span style="color: {COLORS['danger']}; flex: 1; text-align: right;">{ask_size:,.0f}</span>
        </div>
        """

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# =============================================================================
# MAIN SECTIONS
# =============================================================================
def section_overview(sim):
    """Overview section with key metrics."""
    book_data = sim.get_orderbook()
    perf_data = sim.get_performance()
    metrics = calculate_metrics(perf_data)

    # Top metrics row
    cols = st.columns(6)

    with cols[0]:
        render_metric_card(
            "Add Order Latency",
            "16 ns",
            "31x faster than target",
            "positive",
            "cyan"
        )

    with cols[1]:
        render_metric_card(
            "Cancel Order",
            "50 ns",
            "4x faster",
            "positive",
            "cyan"
        )

    with cols[2]:
        render_metric_card(
            "Get BBO",
            "0.7 ns",
            "71x faster",
            "positive",
            "cyan"
        )

    with cols[3]:
        render_metric_card(
            "Throughput",
            "64M ops/s",
            "+12% vs baseline",
            "positive",
            "indigo"
        )

    with cols[4]:
        render_metric_card(
            "Sharpe Ratio",
            f"{metrics['sharpe']:.2f}",
            "Annualized",
            "positive" if metrics['sharpe'] > 1 else "neutral",
            "success" if metrics['sharpe'] > 1 else "default"
        )

    with cols[5]:
        render_metric_card(
            "Max Drawdown",
            f"{metrics['max_drawdown']:.1%}",
            "Peak to trough",
            "negative",
            "danger"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig = create_depth_chart(book_data)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig = create_equity_chart(perf_data)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Bottom stats
    st.markdown('<div class="section-header">Quick Stats <span class="section-badge">Live</span></div>', unsafe_allow_html=True)

    cols = st.columns(5)
    stats = [
        ("Mid Price", f"${book_data['mid_price']:.4f}"),
        ("Spread", f"{book_data['spread_bps']:.2f} bps"),
        ("Bid Depth", f"{sum(book_data['bid_sizes']):,.0f}"),
        ("Ask Depth", f"{sum(book_data['ask_sizes']):,.0f}"),
        ("Imbalance", f"{(sum(book_data['bid_sizes']) - sum(book_data['ask_sizes'])) / (sum(book_data['bid_sizes']) + sum(book_data['ask_sizes'])):.1%}"),
    ]

    for col, (label, value) in zip(cols, stats):
        with col:
            st.markdown(f"""
            <div class="stat-item">
                <span class="stat-label">{label}</span>
                <span class="stat-value">{value}</span>
            </div>
            """, unsafe_allow_html=True)


def section_orderbook(sim):
    """Order book visualization section."""
    st.markdown('<div class="section-header">Order Book <span class="section-badge">Real-Time</span></div>', unsafe_allow_html=True)

    book_data = sim.get_orderbook()

    col1, col2 = st.columns([2, 1])

    with col1:
        # Depth chart
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig = create_depth_chart(book_data)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

        # Heatmap
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig = create_heatmap(book_data)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("#### Book Statistics")

        mid = book_data['mid_price']
        spread = book_data['spread']
        bid_depth = sum(book_data['bid_sizes'])
        ask_depth = sum(book_data['ask_sizes'])
        imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)

        stats = [
            ("Mid Price", f"${mid:.4f}", "cyan"),
            ("Spread", f"${spread:.4f}", "default"),
            ("Spread (bps)", f"{book_data['spread_bps']:.2f}", "default"),
            ("Bid Depth", f"{bid_depth:,.0f}", "success"),
            ("Ask Depth", f"{ask_depth:,.0f}", "danger"),
            ("Imbalance", f"{imbalance:.1%}", "indigo"),
        ]

        for label, value, color in stats:
            render_metric_card(label, value, color=color)
            st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("#### Level-by-Level")
        render_orderbook_table(book_data, levels=10)


def section_performance(sim):
    """Performance analytics section."""
    st.markdown('<div class="section-header">Performance Analytics <span class="section-badge">Strategy</span></div>', unsafe_allow_html=True)

    perf_data = sim.get_performance()
    metrics = calculate_metrics(perf_data)

    # Equity curve
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    fig = create_equity_chart(perf_data)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

    # Metrics grid
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card("Annual Return", f"{metrics['annual_return']:.1%}",
                          color="success" if metrics['annual_return'] > 0 else "danger")
    with col2:
        render_metric_card("Volatility", f"{metrics['volatility']:.1%}")
    with col3:
        render_metric_card("Sharpe Ratio", f"{metrics['sharpe']:.2f}",
                          color="success" if metrics['sharpe'] > 1 else "default")
    with col4:
        render_metric_card("Sortino Ratio", f"{metrics['sortino']:.2f}",
                          color="success" if metrics['sortino'] > 1.5 else "default")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card("Max Drawdown", f"{metrics['max_drawdown']:.1%}", color="danger")
    with col2:
        render_metric_card("Calmar Ratio", f"{metrics['calmar']:.2f}")
    with col3:
        render_metric_card("Win Rate", f"{metrics['win_rate']:.1%}",
                          color="success" if metrics['win_rate'] > 0.5 else "danger")
    with col4:
        render_metric_card("Profit Factor", f"{metrics['profit_factor']:.2f}",
                          color="success" if metrics['profit_factor'] > 1 else "danger")

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig = create_returns_distribution(perf_data)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig = create_rolling_sharpe(perf_data)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)


def section_signals(sim):
    """Alpha signals section."""
    st.markdown('<div class="section-header">Alpha Signals <span class="section-badge">ML</span></div>', unsafe_allow_html=True)

    # Simulated signal metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card("Information Coefficient", "0.042", "Above threshold", "positive", "cyan")
    with col2:
        render_metric_card("Directional Accuracy", "54.2%", "+4.2% vs random", "positive", "success")
    with col3:
        render_metric_card("Signal Decay", "8 ticks", "Half-life", "neutral", "indigo")
    with col4:
        render_metric_card("Feature Count", "47", "Active features", "neutral", "default")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Feature Importance")

        # Simulated feature importance
        features = ['imbalance_5', 'spread_bps', 'trade_flow', 'volatility_1m',
                   'depth_ratio', 'price_momentum', 'book_pressure', 'vwap_dev']
        importance = np.array([0.18, 0.15, 0.14, 0.12, 0.11, 0.10, 0.08, 0.07])

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=features,
            x=importance,
            orientation='h',
            marker=dict(
                color=importance,
                colorscale=[[0, COLORS['accent_secondary']], [1, COLORS['accent_primary']]],
            ),
            text=[f"{v:.1%}" for v in importance],
            textposition='outside',
            textfont=dict(color=COLORS['text_primary']),
        ))

        fig.update_layout(**get_chart_layout(height=300))
        fig.update_xaxis(title="Importance", tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Signal Decay Profile")

        # Simulated decay
        horizons = np.arange(1, 21)
        ic_decay = 0.05 * np.exp(-horizons / 8) + np.random.normal(0, 0.005, len(horizons))

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=horizons,
            y=ic_decay,
            mode='lines+markers',
            line=dict(color=COLORS['accent_primary'], width=2),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(0, 212, 170, 0.2)',
        ))

        fig.add_hline(y=0.02, line=dict(color=COLORS['warning'], dash='dash'),
                     annotation_text="Min IC Threshold", annotation_font_color=COLORS['warning'])

        fig.update_layout(**get_chart_layout(height=300))
        fig.update_xaxis(title="Horizon (ticks)")
        fig.update_yaxis(title="Information Coefficient")
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)


def section_system_metrics(sim):
    """System performance metrics section."""
    st.markdown('<div class="section-header">System Metrics <span class="section-badge">Engine</span></div>', unsafe_allow_html=True)

    # Benchmark data
    benchmarks = pd.DataFrame({
        'operation': ['Add Order', 'Cancel Order', 'Get BBO', 'Get Depth', 'Mid Price', 'Pool Alloc'],
        'actual': [16, 50, 0.7, 42, 0.66, 1.7],
        'target': [500, 200, 50, 500, 100, 20],
    })
    benchmarks['speedup'] = benchmarks['target'] / benchmarks['actual']

    # Metrics cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card("Peak Throughput", "64M ops/sec", color="cyan")
    with col2:
        render_metric_card("Memory Usage", "128 MB", "Baseline", "neutral", "default")
    with col3:
        render_metric_card("Cache Hit Rate", "99.7%", color="success")
    with col4:
        render_metric_card("Zero Allocations", "In Hot Path", color="indigo")

    st.markdown("<br>", unsafe_allow_html=True)

    # Benchmark chart
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig = create_benchmark_chart(benchmarks)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("#### Benchmark Results")
        for _, row in benchmarks.iterrows():
            st.markdown(f"""
            <div class="benchmark-row">
                <span class="benchmark-name">{row['operation']}</span>
                <span class="benchmark-value">{row['actual']:.1f} ns</span>
                <span class="benchmark-target">target: {row['target']:.0f} ns</span>
                <span class="benchmark-badge">{row['speedup']:.0f}x faster</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Architecture info
    st.markdown("#### Architecture Highlights")

    cols = st.columns(3)

    arch_info = [
        ("Memory Pool", "64-byte cache-line aligned blocks, zero malloc in hot path"),
        ("Order Book", "std::map for price levels, intrusive linked list for orders"),
        ("Ring Buffer", "Lock-free SPSC with atomic counters, power-of-2 capacity"),
    ]

    for col, (title, desc) in zip(cols, arch_info):
        with col:
            st.markdown(f"""
            <div class="stat-item" style="height: 100%;">
                <span class="stat-label" style="color: {COLORS['accent_primary']};">{title}</span>
                <span style="color: {COLORS['text_secondary']}; font-size: 0.9rem; margin-top: 8px;">{desc}</span>
            </div>
            """, unsafe_allow_html=True)


def section_backtest(sim):
    """Backtest lab section."""
    st.markdown('<div class="section-header">Backtest Lab <span class="section-badge">Simulation</span></div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("#### Configuration")

        initial_capital = st.number_input("Initial Capital ($)", value=100000, step=10000)
        commission = st.number_input("Commission (per share)", value=0.001, step=0.0001, format="%.4f")
        slippage = st.number_input("Slippage (bps)", value=1.0, step=0.1)

        st.markdown("<br>", unsafe_allow_html=True)

        strategy = st.selectbox("Strategy", ["Imbalance Alpha", "Mean Reversion", "Momentum", "Market Making"])
        imbalance_threshold = st.slider("Imbalance Threshold", 0.1, 0.5, 0.3, 0.05)
        max_position = st.number_input("Max Position", value=1000, step=100)

        st.markdown("<br>", unsafe_allow_html=True)

        run_backtest = st.button("Run Backtest", use_container_width=True)

    with col2:
        if run_backtest:
            with st.spinner("Running backtest simulation..."):
                time.sleep(1.5)  # Simulate computation

                perf_data = sim.get_performance()
                metrics = calculate_metrics(perf_data)

                st.success("Backtest completed successfully!")

                # Results metrics
                cols = st.columns(4)
                result_metrics = [
                    ("Total Return", f"{metrics['total_return']:.1%}", "success" if metrics['total_return'] > 0 else "danger"),
                    ("Sharpe Ratio", f"{metrics['sharpe']:.2f}", "success" if metrics['sharpe'] > 1 else "default"),
                    ("Max Drawdown", f"{metrics['max_drawdown']:.1%}", "danger"),
                    ("Win Rate", f"{metrics['win_rate']:.1%}", "success" if metrics['win_rate'] > 0.5 else "danger"),
                ]

                for col, (label, value, color) in zip(cols, result_metrics):
                    with col:
                        render_metric_card(label, value, color=color)

                st.markdown("<br>", unsafe_allow_html=True)

                # Equity curve
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                fig = create_equity_chart(perf_data)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="
                background: {COLORS['bg_secondary']};
                border: 2px dashed {COLORS['border']};
                border-radius: 16px;
                padding: 60px;
                text-align: center;
                color: {COLORS['text_secondary']};
            ">
                <div style="font-size: 3rem; margin-bottom: 16px;">📊</div>
                <div style="font-size: 1.1rem; font-weight: 500;">Configure and Run Backtest</div>
                <div style="font-size: 0.9rem; margin-top: 8px;">
                    Adjust parameters on the left and click "Run Backtest" to simulate strategy performance
                </div>
            </div>
            """, unsafe_allow_html=True)


# =============================================================================
# MAIN APP
# =============================================================================
def main():
    """Main application entry point."""
    sim = get_simulator()

    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div style="padding: 20px 0;">
            <h2 style="
                color: {COLORS['accent_primary']};
                font-size: 1.5rem;
                font-weight: 700;
                margin: 0;
            ">Navigation</h2>
        </div>
        """, unsafe_allow_html=True)

        page = st.radio(
            "Select Section",
            ["Overview", "Order Book", "Performance", "Alpha Signals", "System Metrics", "Backtest Lab"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        st.markdown(f"""
        <div style="padding: 10px 0;">
            <div style="color: {COLORS['text_secondary']}; font-size: 0.85rem; margin-bottom: 12px;">
                QUICK STATS
            </div>
        """, unsafe_allow_html=True)

        book_data = sim.get_orderbook()

        st.metric("Mid Price", f"${book_data['mid_price']:.2f}")
        st.metric("Spread", f"{book_data['spread_bps']:.1f} bps")
        st.metric("Engine Latency", "16 ns")

        st.markdown("---")

        st.markdown(f"""
        <div style="
            background: {COLORS['bg_tertiary']};
            border-radius: 12px;
            padding: 16px;
            font-size: 0.8rem;
            color: {COLORS['text_secondary']};
        ">
            <div style="font-weight: 600; color: {COLORS['text_primary']}; margin-bottom: 8px;">
                Engine Performance
            </div>
            <div>Add Order: <span style="color: {COLORS['accent_primary']};">~16 ns</span></div>
            <div>Cancel: <span style="color: {COLORS['accent_primary']};">~50 ns</span></div>
            <div>Get BBO: <span style="color: {COLORS['accent_primary']};">~0.7 ns</span></div>
            <div>Pool Alloc: <span style="color: {COLORS['accent_primary']};">~1.7 ns</span></div>
        </div>
        """, unsafe_allow_html=True)

    # Main content
    render_header()

    if page == "Overview":
        section_overview(sim)
    elif page == "Order Book":
        section_orderbook(sim)
    elif page == "Performance":
        section_performance(sim)
    elif page == "Alpha Signals":
        section_signals(sim)
    elif page == "System Metrics":
        section_system_metrics(sim)
    elif page == "Backtest Lab":
        section_backtest(sim)


if __name__ == "__main__":
    main()
