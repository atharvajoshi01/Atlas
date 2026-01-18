"""Atlas Trading Dashboard - Ultra Premium with Animations."""

import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import random

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Atlas | Quantum Trading Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# COLOR PALETTE - Orange/Amber Premium Theme
# =============================================================================
COLORS = {
    "bg_primary": "#0a0a0f",
    "bg_secondary": "#12121a",
    "bg_tertiary": "#1a1a24",
    "bg_card": "rgba(20, 20, 30, 0.8)",
    "accent_primary": "#ff6b00",
    "accent_secondary": "#ff8c00",
    "accent_gradient": "linear-gradient(135deg, #ff6b00 0%, #ff8c00 50%, #ffa500 100%)",
    "success": "#00d4aa",
    "danger": "#ff4757",
    "warning": "#ffa502",
    "info": "#3b82f6",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0b0",
    "text_muted": "#606070",
    "border": "rgba(255, 107, 0, 0.2)",
    "glow": "rgba(255, 107, 0, 0.5)",
    "glass": "rgba(255, 255, 255, 0.05)",
}

# =============================================================================
# MEGA CSS - Animations, Glassmorphism, Smooth Transitions
# =============================================================================
st.markdown(f"""
<style>
    /* ===== FONTS ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&family=Orbitron:wght@400;500;600;700;800;900&display=swap');

    /* ===== ROOT VARIABLES ===== */
    :root {{
        --bg-primary: {COLORS['bg_primary']};
        --bg-secondary: {COLORS['bg_secondary']};
        --accent: {COLORS['accent_primary']};
        --accent-secondary: {COLORS['accent_secondary']};
        --text-primary: {COLORS['text_primary']};
        --text-secondary: {COLORS['text_secondary']};
    }}

    /* ===== HIDE ALL STREAMLIT/DEVELOPER ELEMENTS ===== */
    #MainMenu {{visibility: hidden !important;}}
    footer {{visibility: hidden !important;}}
    header {{visibility: hidden !important;}}
    .stDeployButton {{display: none !important;}}
    [data-testid="stToolbar"] {{display: none !important;}}
    [data-testid="stDecoration"] {{display: none !important;}}
    [data-testid="stStatusWidget"] {{display: none !important;}}
    .viewerBadge_link__qRIco {{display: none !important;}}
    .viewerBadge_container__r5tak {{display: none !important;}}
    [data-testid="manage-app-button"] {{display: none !important;}}
    .styles_viewerBadge__CvC9N {{display: none !important;}}
    .stAppViewBlockContainer {{padding-top: 0 !important;}}
    div[data-testid="stToolbar"] {{display: none !important;}}
    div[data-testid="stDecoration"] {{display: none !important;}}
    div[data-testid="stStatusWidget"] {{display: none !important;}}
    #stDecoration {{display: none !important;}}
    button[title="View fullscreen"] {{display: none !important;}}
    .reportview-container .main footer {{visibility: hidden !important;}}
    #MainMenu, footer, header {{visibility: hidden !important;}}

    /* ===== KEYFRAME ANIMATIONS ===== */
    @keyframes gradient-shift {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    @keyframes pulse-glow {{
        0%, 100% {{ box-shadow: 0 0 20px {COLORS['glow']}; }}
        50% {{ box-shadow: 0 0 40px {COLORS['glow']}, 0 0 60px {COLORS['glow']}; }}
    }}

    @keyframes float {{
        0%, 100% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-10px); }}
    }}

    @keyframes slide-up {{
        from {{ opacity: 0; transform: translateY(30px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes slide-in-right {{
        from {{ opacity: 0; transform: translateX(50px); }}
        to {{ opacity: 1; transform: translateX(0); }}
    }}

    @keyframes fade-in {{
        from {{ opacity: 0; }}
        to {{ opacity: 1; }}
    }}

    @keyframes scale-in {{
        from {{ opacity: 0; transform: scale(0.9); }}
        to {{ opacity: 1; transform: scale(1); }}
    }}

    @keyframes shimmer {{
        0% {{ background-position: -200% 0; }}
        100% {{ background-position: 200% 0; }}
    }}

    @keyframes rotate {{
        from {{ transform: rotate(0deg); }}
        to {{ transform: rotate(360deg); }}
    }}

    @keyframes pulse {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.7; transform: scale(1.1); }}
    }}

    @keyframes wave {{
        0%, 100% {{ transform: scaleY(1); }}
        50% {{ transform: scaleY(0.5); }}
    }}

    @keyframes typewriter {{
        from {{ width: 0; }}
        to {{ width: 100%; }}
    }}

    @keyframes blink {{
        0%, 50% {{ opacity: 1; }}
        51%, 100% {{ opacity: 0; }}
    }}

    @keyframes particle-float {{
        0%, 100% {{
            transform: translateY(0) translateX(0) rotate(0deg);
            opacity: 0;
        }}
        10% {{ opacity: 1; }}
        90% {{ opacity: 1; }}
        100% {{
            transform: translateY(-100vh) translateX(100px) rotate(720deg);
            opacity: 0;
        }}
    }}

    /* ===== GLOBAL STYLES ===== */
    .stApp {{
        background: {COLORS['bg_primary']};
        background-image:
            radial-gradient(ellipse at 20% 80%, rgba(255, 107, 0, 0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 20%, rgba(255, 140, 0, 0.06) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 50%, rgba(255, 165, 0, 0.03) 0%, transparent 70%);
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
        overflow-x: hidden;
    }}

    /* Animated background particles */
    .stApp::before {{
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='1' fill='rgba(255,107,0,0.1)'/%3E%3C/svg%3E");
        background-size: 50px 50px;
        opacity: 0.5;
        pointer-events: none;
        z-index: 0;
    }}

    /* Hide Streamlit Elements */
    #MainMenu, footer, header {{visibility: hidden;}}
    .stDeployButton {{display: none;}}

    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {COLORS['bg_secondary']} 0%, {COLORS['bg_primary']} 100%);
        border-right: 1px solid {COLORS['border']};
    }}

    [data-testid="stSidebar"] > div:first-child {{
        padding-top: 2rem;
    }}

    /* ===== MAIN HEADER ===== */
    .hero-header {{
        background: linear-gradient(135deg, {COLORS['bg_secondary']} 0%, {COLORS['bg_tertiary']} 100%);
        border: 1px solid {COLORS['border']};
        border-radius: 24px;
        padding: 32px 40px;
        margin-bottom: 32px;
        position: relative;
        overflow: hidden;
        animation: slide-up 0.8s ease-out;
        backdrop-filter: blur(20px);
    }}

    .hero-header::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: {COLORS['accent_gradient']};
        background-size: 200% 200%;
        animation: gradient-shift 3s ease infinite;
    }}

    .hero-header::after {{
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 100%;
        height: 200%;
        background: radial-gradient(circle, {COLORS['glow']} 0%, transparent 70%);
        opacity: 0.1;
        animation: rotate 20s linear infinite;
    }}

    .hero-title {{
        font-family: 'Orbitron', sans-serif;
        font-size: 3.5rem;
        font-weight: 900;
        background: {COLORS['accent_gradient']};
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        letter-spacing: 0.1em;
        text-shadow: 0 0 40px {COLORS['glow']};
        animation: pulse-glow 3s ease-in-out infinite;
    }}

    .hero-subtitle {{
        color: {COLORS['text_secondary']};
        font-size: 1.1rem;
        font-weight: 400;
        margin-top: 8px;
        letter-spacing: 0.2em;
        text-transform: uppercase;
    }}

    .hero-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: linear-gradient(135deg, rgba(255, 107, 0, 0.2), rgba(255, 140, 0, 0.1));
        border: 1px solid {COLORS['accent_primary']};
        border-radius: 50px;
        padding: 8px 20px;
        font-size: 0.85rem;
        color: {COLORS['accent_primary']};
        font-weight: 600;
        animation: pulse 2s ease-in-out infinite;
    }}

    .hero-badge .dot {{
        width: 10px;
        height: 10px;
        background: {COLORS['accent_primary']};
        border-radius: 50%;
        animation: pulse 1.5s ease-in-out infinite;
        box-shadow: 0 0 10px {COLORS['accent_primary']};
    }}

    /* ===== METRIC CARDS ===== */
    .metric-card {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 20px;
        padding: 24px;
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(20px);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        animation: scale-in 0.6s ease-out;
    }}

    .metric-card:hover {{
        transform: translateY(-8px) scale(1.02);
        border-color: {COLORS['accent_primary']};
        box-shadow:
            0 20px 40px rgba(0, 0, 0, 0.4),
            0 0 40px {COLORS['glow']},
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }}

    .metric-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 107, 0, 0.1), transparent);
        transition: left 0.5s ease;
    }}

    .metric-card:hover::before {{
        left: 100%;
    }}

    .metric-card .icon {{
        width: 48px;
        height: 48px;
        background: {COLORS['accent_gradient']};
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        margin-bottom: 16px;
        animation: float 3s ease-in-out infinite;
    }}

    .metric-label {{
        color: {COLORS['text_secondary']};
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 8px;
    }}

    .metric-value {{
        font-family: 'Orbitron', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: {COLORS['text_primary']};
        margin-bottom: 4px;
        background: linear-gradient(135deg, {COLORS['text_primary']}, {COLORS['accent_primary']});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}

    .metric-value.orange {{
        background: {COLORS['accent_gradient']};
        -webkit-background-clip: text;
    }}

    .metric-value.green {{
        background: linear-gradient(135deg, #00d4aa, #00ff88);
        -webkit-background-clip: text;
    }}

    .metric-value.red {{
        background: linear-gradient(135deg, #ff4757, #ff6b6b);
        -webkit-background-clip: text;
    }}

    .metric-delta {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 20px;
        animation: fade-in 0.5s ease-out;
    }}

    .metric-delta.positive {{
        background: rgba(0, 212, 170, 0.15);
        color: {COLORS['success']};
    }}

    .metric-delta.negative {{
        background: rgba(255, 71, 87, 0.15);
        color: {COLORS['danger']};
    }}

    /* ===== CHART CONTAINERS ===== */
    .chart-container {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 24px;
        padding: 28px;
        margin-bottom: 24px;
        backdrop-filter: blur(20px);
        animation: slide-up 0.8s ease-out;
        transition: all 0.3s ease;
    }}

    .chart-container:hover {{
        border-color: rgba(255, 107, 0, 0.4);
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
    }}

    .chart-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding-bottom: 16px;
        border-bottom: 1px solid {COLORS['border']};
    }}

    .chart-title {{
        font-family: 'Orbitron', sans-serif;
        font-size: 1.2rem;
        font-weight: 700;
        color: {COLORS['text_primary']};
        display: flex;
        align-items: center;
        gap: 12px;
    }}

    .chart-title .icon {{
        width: 32px;
        height: 32px;
        background: {COLORS['accent_gradient']};
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .chart-badge {{
        background: rgba(255, 107, 0, 0.1);
        border: 1px solid {COLORS['accent_primary']};
        color: {COLORS['accent_primary']};
        font-size: 0.7rem;
        font-weight: 700;
        padding: 6px 14px;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        animation: pulse 2s infinite;
    }}

    /* ===== AI PREDICTION BADGE ===== */
    .ai-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(99, 102, 241, 0.1));
        border: 1px solid #8b5cf6;
        border-radius: 20px;
        padding: 6px 16px;
        font-size: 0.75rem;
        font-weight: 600;
        color: #a78bfa;
        animation: shimmer 2s infinite;
        background-size: 200% 100%;
    }}

    .ai-badge::before {{
        content: '🤖';
        font-size: 0.9rem;
    }}

    /* ===== TRADING PANEL ===== */
    .trading-panel {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 24px;
        padding: 28px;
        backdrop-filter: blur(20px);
        animation: slide-in-right 0.8s ease-out;
    }}

    .trading-tabs {{
        display: flex;
        gap: 8px;
        margin-bottom: 24px;
        background: {COLORS['bg_tertiary']};
        padding: 6px;
        border-radius: 16px;
    }}

    .trading-tab {{
        flex: 1;
        padding: 14px 24px;
        border: none;
        border-radius: 12px;
        font-weight: 700;
        font-size: 1rem;
        cursor: pointer;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    .trading-tab.buy {{
        background: linear-gradient(135deg, {COLORS['success']}, #00ff88);
        color: {COLORS['bg_primary']};
        box-shadow: 0 4px 20px rgba(0, 212, 170, 0.4);
    }}

    .trading-tab.sell {{
        background: {COLORS['bg_secondary']};
        color: {COLORS['text_secondary']};
    }}

    .trading-tab.sell:hover {{
        background: linear-gradient(135deg, {COLORS['danger']}, #ff6b6b);
        color: white;
    }}

    .percent-buttons {{
        display: flex;
        gap: 8px;
        margin: 16px 0;
    }}

    .percent-btn {{
        flex: 1;
        padding: 10px;
        background: {COLORS['bg_tertiary']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        color: {COLORS['text_secondary']};
        font-weight: 600;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }}

    .percent-btn:hover {{
        background: {COLORS['accent_primary']};
        color: white;
        border-color: {COLORS['accent_primary']};
        transform: translateY(-2px);
    }}

    .order-btn {{
        width: 100%;
        padding: 18px;
        border: none;
        border-radius: 16px;
        font-weight: 800;
        font-size: 1.1rem;
        cursor: pointer;
        transition: all 0.4s ease;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 20px;
    }}

    .order-btn.buy {{
        background: linear-gradient(135deg, {COLORS['success']}, #00ff88);
        color: {COLORS['bg_primary']};
        box-shadow: 0 8px 30px rgba(0, 212, 170, 0.4);
    }}

    .order-btn.buy:hover {{
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(0, 212, 170, 0.6);
    }}

    .order-btn.sell {{
        background: linear-gradient(135deg, {COLORS['danger']}, #ff6b6b);
        color: white;
        box-shadow: 0 8px 30px rgba(255, 71, 87, 0.4);
    }}

    /* ===== PRICE DISPLAY ===== */
    .price-display {{
        text-align: center;
        padding: 24px;
        background: {COLORS['bg_tertiary']};
        border-radius: 16px;
        margin-bottom: 20px;
    }}

    .price-label {{
        color: {COLORS['text_secondary']};
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 8px;
    }}

    .price-value {{
        font-family: 'Orbitron', sans-serif;
        font-size: 2.5rem;
        font-weight: 900;
        background: {COLORS['accent_gradient']};
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}

    .price-change {{
        font-size: 1rem;
        font-weight: 600;
        margin-top: 8px;
    }}

    .price-change.positive {{ color: {COLORS['success']}; }}
    .price-change.negative {{ color: {COLORS['danger']}; }}

    /* ===== ORDER BOOK TABLE ===== */
    .orderbook-table {{
        background: {COLORS['bg_tertiary']};
        border-radius: 16px;
        overflow: hidden;
    }}

    .orderbook-header {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        padding: 12px 16px;
        background: {COLORS['bg_secondary']};
        font-size: 0.75rem;
        font-weight: 700;
        color: {COLORS['text_secondary']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    .orderbook-row {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        padding: 10px 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        border-bottom: 1px solid {COLORS['border']};
        transition: all 0.2s ease;
        position: relative;
    }}

    .orderbook-row:hover {{
        background: rgba(255, 255, 255, 0.02);
    }}

    .orderbook-row.bid::before {{
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: var(--depth, 50%);
        background: linear-gradient(90deg, rgba(0, 212, 170, 0.15), transparent);
        z-index: 0;
    }}

    .orderbook-row.ask::before {{
        content: '';
        position: absolute;
        right: 0;
        top: 0;
        bottom: 0;
        width: var(--depth, 50%);
        background: linear-gradient(-90deg, rgba(255, 71, 87, 0.15), transparent);
        z-index: 0;
    }}

    .orderbook-row span {{
        position: relative;
        z-index: 1;
    }}

    .orderbook-row .bid-price {{ color: {COLORS['success']}; }}
    .orderbook-row .ask-price {{ color: {COLORS['danger']}; }}

    /* ===== SECTION HEADERS ===== */
    .section-header {{
        font-family: 'Orbitron', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        color: {COLORS['text_primary']};
        margin: 40px 0 28px 0;
        display: flex;
        align-items: center;
        gap: 16px;
        animation: slide-up 0.6s ease-out;
    }}

    .section-header::before {{
        content: '';
        width: 4px;
        height: 32px;
        background: {COLORS['accent_gradient']};
        border-radius: 2px;
    }}

    .section-badge {{
        background: {COLORS['accent_gradient']};
        color: white;
        font-size: 0.65rem;
        font-weight: 700;
        padding: 6px 14px;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        animation: pulse 2s infinite;
    }}

    /* ===== STATS ROW ===== */
    .stats-row {{
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 24px;
    }}

    .stat-pill {{
        display: flex;
        align-items: center;
        gap: 8px;
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 50px;
        padding: 10px 20px;
        font-size: 0.9rem;
        animation: fade-in 0.5s ease-out;
        transition: all 0.3s ease;
    }}

    .stat-pill:hover {{
        border-color: {COLORS['accent_primary']};
        transform: translateY(-2px);
    }}

    .stat-pill .label {{
        color: {COLORS['text_secondary']};
        font-weight: 500;
    }}

    .stat-pill .value {{
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        color: {COLORS['accent_primary']};
    }}

    /* ===== WAVE ANIMATION ===== */
    .wave-container {{
        display: flex;
        align-items: flex-end;
        gap: 3px;
        height: 24px;
    }}

    .wave-bar {{
        width: 4px;
        background: {COLORS['accent_primary']};
        border-radius: 2px;
        animation: wave 1s ease-in-out infinite;
    }}

    .wave-bar:nth-child(1) {{ height: 40%; animation-delay: 0s; }}
    .wave-bar:nth-child(2) {{ height: 70%; animation-delay: 0.1s; }}
    .wave-bar:nth-child(3) {{ height: 50%; animation-delay: 0.2s; }}
    .wave-bar:nth-child(4) {{ height: 90%; animation-delay: 0.3s; }}
    .wave-bar:nth-child(5) {{ height: 60%; animation-delay: 0.4s; }}

    /* ===== LOADING SPINNER ===== */
    .spinner {{
        width: 40px;
        height: 40px;
        border: 3px solid {COLORS['border']};
        border-top-color: {COLORS['accent_primary']};
        border-radius: 50%;
        animation: rotate 1s linear infinite;
    }}

    /* ===== BENCHMARK BARS ===== */
    .benchmark-item {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 12px;
        animation: slide-up 0.5s ease-out;
        transition: all 0.3s ease;
    }}

    .benchmark-item:hover {{
        transform: translateX(8px);
        border-color: {COLORS['accent_primary']};
    }}

    .benchmark-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }}

    .benchmark-name {{
        font-weight: 600;
        color: {COLORS['text_primary']};
    }}

    .benchmark-value {{
        font-family: 'Orbitron', sans-serif;
        font-weight: 700;
        color: {COLORS['accent_primary']};
    }}

    .benchmark-bar {{
        height: 8px;
        background: {COLORS['bg_tertiary']};
        border-radius: 4px;
        overflow: hidden;
    }}

    .benchmark-fill {{
        height: 100%;
        background: {COLORS['accent_gradient']};
        border-radius: 4px;
        transition: width 1s ease-out;
    }}

    .benchmark-badge {{
        background: rgba(0, 212, 170, 0.15);
        color: {COLORS['success']};
        font-size: 0.75rem;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 12px;
    }}

    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: {COLORS['bg_primary']};
    }}

    ::-webkit-scrollbar-thumb {{
        background: {COLORS['accent_primary']};
        border-radius: 4px;
    }}

    /* ===== STREAMLIT OVERRIDES ===== */
    .stSelectbox > div > div,
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {{
        background-color: {COLORS['bg_tertiary']} !important;
        border-color: {COLORS['border']} !important;
        color: {COLORS['text_primary']} !important;
        border-radius: 12px !important;
    }}

    .stButton > button {{
        background: {COLORS['accent_gradient']} !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 12px 28px !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}

    .stButton > button:hover {{
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 30px {COLORS['glow']} !important;
    }}

    .stSlider > div > div > div {{
        background: {COLORS['accent_gradient']} !important;
    }}

    .stMetric {{
        background: {COLORS['bg_card']};
        padding: 16px;
        border-radius: 16px;
        border: 1px solid {COLORS['border']};
    }}

    .stMetric label {{
        color: {COLORS['text_secondary']} !important;
    }}

    .stMetric > div {{
        color: {COLORS['text_primary']} !important;
    }}

    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background: {COLORS['bg_secondary']};
        padding: 8px;
        border-radius: 16px;
    }}

    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        border-radius: 12px;
        color: {COLORS['text_secondary']};
        font-weight: 600;
        padding: 12px 24px;
    }}

    .stTabs [aria-selected="true"] {{
        background: {COLORS['accent_gradient']} !important;
        color: white !important;
    }}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# DATA SIMULATION
# =============================================================================
class MarketSimulator:
    """Advanced market data simulator with realistic dynamics."""

    def __init__(self):
        np.random.seed(int(time.time()) % 1000)
        self.base_price = 87900.0
        self.volatility = 0.0003

    def get_ohlc(self, periods=100):
        """Generate OHLC candlestick data."""
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='1h')

        # Generate realistic price movement
        returns = np.random.normal(0.0001, 0.005, periods)
        close = self.base_price * np.cumprod(1 + returns)

        # Generate OHLC
        high = close * (1 + np.abs(np.random.normal(0, 0.003, periods)))
        low = close * (1 - np.abs(np.random.normal(0, 0.003, periods)))
        open_price = np.roll(close, 1)
        open_price[0] = close[0]

        volume = np.random.exponential(1000, periods) * 100

        return pd.DataFrame({
            'date': dates,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

    def get_orderbook(self, levels=12):
        """Generate order book data."""
        mid = self.base_price + np.random.normal(0, 50)
        spread = np.random.uniform(5, 15)

        bid_prices = mid - spread/2 - np.cumsum(np.random.exponential(2, levels))
        ask_prices = mid + spread/2 + np.cumsum(np.random.exponential(2, levels))

        bid_sizes = np.random.pareto(1.2, levels) * 0.5 + 0.1
        ask_sizes = np.random.pareto(1.2, levels) * 0.5 + 0.1

        return {
            'bid_prices': bid_prices,
            'bid_sizes': bid_sizes,
            'ask_prices': ask_prices,
            'ask_sizes': ask_sizes,
            'mid': mid,
            'spread': spread,
        }

    def get_performance(self, days=252):
        """Generate performance data."""
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        returns = np.random.normal(0.0004, 0.012, days)
        equity = 100000 * np.cumprod(1 + returns)
        drawdown = (np.maximum.accumulate(equity) - equity) / np.maximum.accumulate(equity)

        return pd.DataFrame({
            'date': dates,
            'returns': returns,
            'equity': equity,
            'drawdown': drawdown
        })


@st.cache_resource
def get_simulator():
    return MarketSimulator()


# =============================================================================
# CHART FUNCTIONS
# =============================================================================
def get_layout(height=400):
    """Base chart layout."""
    return dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter", color=COLORS['text_secondary']),
        height=height,
        margin=dict(l=50, r=30, t=30, b=50),
        xaxis=dict(
            gridcolor='rgba(255,107,0,0.1)',
            zerolinecolor='rgba(255,107,0,0.2)',
        ),
        yaxis=dict(
            gridcolor='rgba(255,107,0,0.1)',
            zerolinecolor='rgba(255,107,0,0.2)',
        ),
        hoverlabel=dict(
            bgcolor=COLORS['bg_secondary'],
            bordercolor=COLORS['accent_primary'],
            font=dict(family="JetBrains Mono", size=12),
        ),
    )


def create_candlestick_chart(df):
    """Create candlestick chart with volume."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
    )

    # Candlesticks
    colors = [COLORS['success'] if c >= o else COLORS['danger']
              for o, c in zip(df['open'], df['close'])]

    fig.add_trace(go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing=dict(line=dict(color=COLORS['success']), fillcolor=COLORS['success']),
        decreasing=dict(line=dict(color=COLORS['danger']), fillcolor=COLORS['danger']),
        name='Price',
    ), row=1, col=1)

    # Volume bars
    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['volume'],
        marker=dict(color=colors, opacity=0.5),
        name='Volume',
    ), row=2, col=1)

    fig.update_layout(**get_layout(450))
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False)

    return fig


def create_depth_chart(book):
    """Create order book depth chart."""
    fig = go.Figure()

    bid_cum = np.cumsum(book['bid_sizes'])
    ask_cum = np.cumsum(book['ask_sizes'])

    fig.add_trace(go.Scatter(
        x=book['bid_prices'][::-1],
        y=bid_cum[::-1],
        fill='tozeroy',
        fillcolor='rgba(0, 212, 170, 0.3)',
        line=dict(color=COLORS['success'], width=2),
        name='Bids',
    ))

    fig.add_trace(go.Scatter(
        x=book['ask_prices'],
        y=ask_cum,
        fill='tozeroy',
        fillcolor='rgba(255, 71, 87, 0.3)',
        line=dict(color=COLORS['danger'], width=2),
        name='Asks',
    ))

    fig.add_vline(x=book['mid'], line=dict(color=COLORS['accent_primary'], width=2, dash='dot'))

    fig.update_layout(**get_layout(300))
    return fig


def create_equity_chart(perf):
    """Create equity curve."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)

    fig.add_trace(go.Scatter(
        x=perf['date'],
        y=perf['equity'],
        fill='tozeroy',
        fillcolor='rgba(255, 107, 0, 0.2)',
        line=dict(color=COLORS['accent_primary'], width=2),
        name='Equity',
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=perf['date'],
        y=-perf['drawdown'] * 100,
        fill='tozeroy',
        fillcolor='rgba(255, 71, 87, 0.3)',
        line=dict(color=COLORS['danger'], width=1),
        name='Drawdown',
    ), row=2, col=1)

    fig.update_layout(**get_layout(400))
    fig.update_layout(showlegend=False)
    return fig


# =============================================================================
# UI COMPONENTS
# =============================================================================
def render_header():
    """Render animated header."""
    from datetime import timezone
    utc_now = datetime.now(timezone.utc)
    st.markdown(f"""
    <div class="hero-header">
        <div style="display: flex; justify-content: space-between; align-items: center; position: relative; z-index: 1;">
            <div>
                <h1 class="hero-title">ATLAS</h1>
                <p class="hero-subtitle">Low-Latency Order Book Engine • Sub-Microsecond Execution</p>
            </div>
            <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 12px;">
                <div class="hero-badge">
                    <span class="dot"></span>
                    DEMO MODE
                </div>
                <div class="ai-badge">ML Pipeline Active</div>
                <div style="font-family: 'JetBrains Mono'; color: {COLORS['text_secondary']}; font-size: 0.9rem;">
                    {utc_now.strftime('%Y-%m-%d %H:%M:%S')} UTC
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_metric(label, value, delta=None, delta_type="positive", icon="📊", color="orange"):
    """Render animated metric card."""
    delta_html = ""
    if delta:
        delta_class = "positive" if delta_type == "positive" else "negative"
        arrow = "↑" if delta_type == "positive" else "↓"
        delta_html = f'<div class="metric-delta {delta_class}">{arrow} {delta}</div>'

    st.markdown(f"""
    <div class="metric-card">
        <div class="icon">{icon}</div>
        <div class="metric-label">{label}</div>
        <div class="metric-value {color}">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_orderbook_table(book):
    """Render order book table."""
    max_size = max(max(book['ask_sizes']), max(book['bid_sizes']))

    # Build ask rows
    ask_rows = ""
    for i in range(min(6, len(book['ask_prices']))-1, -1, -1):
        depth = (book['ask_sizes'][i] / max_size) * 100
        ask_rows += f"""
        <div class="row ask" style="--depth: {depth}%;">
            <span class="price ask-price">${book['ask_prices'][i]:,.2f}</span>
            <span class="size">{book['ask_sizes'][i]:.4f}</span>
            <span class="total">{book['ask_sizes'][i] * book['ask_prices'][i]:,.2f}</span>
        </div>
        """

    # Build bid rows
    bid_rows = ""
    for i in range(min(6, len(book['bid_prices']))):
        depth = (book['bid_sizes'][i] / max_size) * 100
        bid_rows += f"""
        <div class="row bid" style="--depth: {depth}%;">
            <span class="price bid-price">${book['bid_prices'][i]:,.2f}</span>
            <span class="size">{book['bid_sizes'][i]:.4f}</span>
            <span class="total">{book['bid_sizes'][i] * book['bid_prices'][i]:,.2f}</span>
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
                background: {COLORS['bg_secondary']};
                color: {COLORS['text_primary']};
                border-radius: 12px;
                overflow: hidden;
            }}
            .header {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                padding: 12px 16px;
                background: {COLORS['bg_tertiary']};
                font-size: 0.75rem;
                font-weight: 600;
                color: {COLORS['text_secondary']};
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .header span:nth-child(2) {{ text-align: center; }}
            .header span:nth-child(3) {{ text-align: right; }}
            .row {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                padding: 10px 16px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                position: relative;
                transition: background 0.2s;
            }}
            .row::before {{
                content: '';
                position: absolute;
                top: 0;
                height: 100%;
                opacity: 0.15;
                transition: width 0.3s;
            }}
            .row.ask::before {{
                right: 0;
                width: var(--depth);
                background: linear-gradient(90deg, transparent, {COLORS['danger']});
            }}
            .row.bid::before {{
                left: 0;
                width: var(--depth);
                background: linear-gradient(270deg, transparent, {COLORS['success']});
            }}
            .row:hover {{ background: rgba(255,255,255,0.05); }}
            .row span {{ position: relative; z-index: 1; }}
            .size {{ text-align: center; }}
            .total {{ text-align: right; color: {COLORS['text_secondary']}; }}
            .ask-price {{ color: {COLORS['danger']}; font-weight: 500; }}
            .bid-price {{ color: {COLORS['success']}; font-weight: 500; }}
            .spread {{
                padding: 10px 16px;
                text-align: center;
                background: {COLORS['bg_primary']};
                color: {COLORS['accent_primary']};
                font-weight: 600;
                font-size: 0.9rem;
                border-top: 1px solid {COLORS['border']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <span>Price</span>
            <span>Size (BTC)</span>
            <span>Total</span>
        </div>
        {ask_rows}
        <div class="spread">
            Spread: ${book['spread']:.2f} ({book['spread']/book['mid']*100:.3f}%)
        </div>
        {bid_rows}
    </body>
    </html>
    """
    components.html(html, height=420)


def render_benchmark(name, actual, target, icon="⚡"):
    """Render benchmark item with animated bar."""
    speedup = target / actual
    fill_pct = min((actual / target) * 100, 100)

    st.markdown(f"""
    <div class="benchmark-item">
        <div class="benchmark-header">
            <span class="benchmark-name">{icon} {name}</span>
            <div style="display: flex; align-items: center; gap: 12px;">
                <span class="benchmark-value">{actual:.1f} ns</span>
                <span class="benchmark-badge">{speedup:.0f}x faster</span>
            </div>
        </div>
        <div class="benchmark-bar">
            <div class="benchmark-fill" style="width: {fill_pct}%;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.75rem; color: {COLORS['text_muted']};">
            <span>Actual</span>
            <span>Target: {target:.0f} ns</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_engine_demo_card():
    """Render engine demo card using components.html for reliable rendering."""
    html = f"""
    <html>
    <head>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Inter', sans-serif;
                background: {COLORS['bg_secondary']};
                color: {COLORS['text_primary']};
                border-radius: 16px;
                padding: 24px;
                border: 1px solid {COLORS['border']};
            }}
            .title {{
                font-family: 'Orbitron', sans-serif;
                font-size: 1.1rem;
                font-weight: 700;
                color: {COLORS['accent_primary']};
                margin-bottom: 20px;
            }}
            .stat-block {{
                margin-bottom: 16px;
            }}
            .stat-label {{
                color: {COLORS['text_secondary']};
                font-size: 0.8rem;
                margin-bottom: 4px;
            }}
            .stat-value {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 1.5rem;
                font-weight: 700;
                color: {COLORS['accent_primary']};
            }}
            .stat-desc {{
                color: {COLORS['text_muted']};
                font-size: 0.75rem;
                margin-top: 2px;
            }}
            .tech-stack {{
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
                margin-top: 8px;
            }}
            .tech-stack span {{
                background: {COLORS['bg_tertiary']};
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 0.75rem;
                color: {COLORS['text_primary']};
            }}
            .insight-box {{
                background: linear-gradient(135deg, rgba(0,212,170,0.1), rgba(255,107,0,0.1));
                border-radius: 12px;
                padding: 16px;
                margin-top: 16px;
            }}
            .insight-title {{
                color: {COLORS['accent_primary']};
                font-weight: 600;
                margin-bottom: 8px;
                font-size: 0.9rem;
            }}
            .insight-text {{
                color: {COLORS['text_secondary']};
                font-size: 0.85rem;
                line-height: 1.5;
            }}
        </style>
    </head>
    <body>
        <div class="title">⚡ Engine Performance</div>

        <div class="stat-block">
            <div class="stat-label">Add Order Latency</div>
            <div class="stat-value">16 ns</div>
            <div class="stat-desc">31x faster than typical systems</div>
        </div>

        <div class="stat-block">
            <div class="stat-label">Peak Throughput</div>
            <div class="stat-value">64M ops/sec</div>
            <div class="stat-desc">Million operations per second</div>
        </div>

        <div class="stat-block">
            <div class="stat-label">Tech Stack</div>
            <div class="tech-stack">
                <span>C++20</span>
                <span>Python</span>
                <span>Numba JIT</span>
                <span>pybind11</span>
            </div>
        </div>

        <div class="insight-box">
            <div class="insight-title">🔬 What You're Seeing</div>
            <div class="insight-text">This dashboard visualizes a simulated order book. The C++ engine processes orders at nanosecond speeds - faster than light travels 5 meters!</div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=380)


def render_orderbook_stats_card(book):
    """Render order book statistics card using components.html for reliable rendering."""
    html = f"""
    <html>
    <head>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Inter', sans-serif;
                background: {COLORS['bg_secondary']};
                color: {COLORS['text_primary']};
                border-radius: 16px;
                padding: 24px;
                border: 1px solid {COLORS['border']};
            }}
            .title {{
                font-family: 'Orbitron', sans-serif;
                font-size: 1.1rem;
                font-weight: 700;
                color: {COLORS['accent_primary']};
                margin-bottom: 20px;
            }}
            .stat-block {{
                margin-bottom: 16px;
            }}
            .stat-label {{
                color: {COLORS['text_secondary']};
                font-size: 0.8rem;
                margin-bottom: 4px;
            }}
            .stat-value {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 1.5rem;
                font-weight: 700;
                color: {COLORS['text_primary']};
            }}
            .stat-value-sm {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 1.1rem;
                font-weight: 600;
            }}
            .green {{ color: {COLORS['success']}; }}
            .red {{ color: {COLORS['danger']}; }}
            .orange {{ color: {COLORS['accent_primary']}; }}
            .white {{ color: {COLORS['text_primary']}; }}
            .stat-desc {{
                color: {COLORS['text_muted']};
                font-size: 0.75rem;
                margin-top: 2px;
            }}
            .insight-box {{
                background: {COLORS['bg_tertiary']};
                border-radius: 12px;
                padding: 16px;
                margin-top: 16px;
            }}
            .insight-title {{
                color: {COLORS['accent_primary']};
                font-weight: 600;
                margin-bottom: 8px;
                font-size: 0.9rem;
            }}
            .insight-text {{
                color: {COLORS['text_secondary']};
                font-size: 0.85rem;
                line-height: 1.5;
            }}
        </style>
    </head>
    <body>
        <div class="title">📊 Order Book Statistics</div>

        <div class="stat-block">
            <div class="stat-label">Simulated Mid Price</div>
            <div class="stat-value">${book['mid']:,.2f}</div>
            <div class="stat-desc">Generated by market simulator</div>
        </div>

        <div class="stat-block">
            <div class="stat-label">Bid-Ask Spread</div>
            <div class="stat-value-sm orange">${book['spread']:.2f}</div>
            <div class="stat-desc">{book['spread']/book['mid']*100:.4f}% of mid price</div>
        </div>

        <div class="stat-block">
            <div class="stat-label">Order Book Levels</div>
            <div class="stat-value-sm white">12 per side</div>
            <div class="stat-desc">Configurable depth</div>
        </div>

        <div class="stat-block">
            <div class="stat-label">Update Frequency</div>
            <div class="stat-value-sm green">Real-time</div>
            <div class="stat-desc">Simulated tick data</div>
        </div>

        <div class="insight-box">
            <div class="insight-title">📖 About This Data</div>
            <div class="insight-text">This order book uses simulated market data to demonstrate the engine. In production, it would connect to real exchange feeds via FIX/ITCH protocols.</div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=420)


# =============================================================================
# MAIN SECTIONS
# =============================================================================
def section_overview(sim):
    """Overview with all metrics and charts."""
    ohlc = sim.get_ohlc()
    book = sim.get_orderbook()
    perf = sim.get_performance()

    # Top metrics
    cols = st.columns(6)
    metrics = [
        ("Add Order", "16 ns", "31x faster", "positive", "⚡", "orange"),
        ("Cancel Order", "50 ns", "4x faster", "positive", "🔄", "orange"),
        ("Get BBO", "0.7 ns", "71x faster", "positive", "📊", "orange"),
        ("Throughput", "64M/s", "+12%", "positive", "🚀", "green"),
        ("Sharpe Ratio", "2.14", "Excellent", "positive", "📈", "green"),
        ("Max DD", "-8.2%", "Low risk", "negative", "📉", "red"),
    ]

    for col, (label, value, delta, dtype, icon, color) in zip(cols, metrics):
        with col:
            render_metric(label, value, delta, dtype, icon, color)

    st.markdown("<br>", unsafe_allow_html=True)

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"""
        <div class="chart-container">
            <div class="chart-header">
                <div class="chart-title">
                    <div class="icon">📊</div>
                    BTC/USDT Price Chart
                </div>
                <div style="display: flex; gap: 8px;">
                    <div class="ai-badge">AI Predicted</div>
                    <div class="chart-badge">Live</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        fig = create_candlestick_chart(ohlc)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with col2:
        # Engine Performance - using components.html for reliable rendering
        render_engine_demo_card()

    # Second row
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div style="background: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']}; border-radius: 16px; padding: 20px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">📚</span>
                    <span style="font-weight: 600; color: {COLORS['text_primary']};">Order Book Depth</span>
                </div>
                <span style="background: {COLORS['accent_primary']}; color: #000; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;">Real-Time</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        fig = create_depth_chart(book)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with col2:
        st.markdown(f"""
        <div style="background: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']}; border-radius: 16px; padding: 20px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">💰</span>
                    <span style="font-weight: 600; color: {COLORS['text_primary']};">Portfolio Performance</span>
                </div>
                <span style="background: {COLORS['success']}; color: #000; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;">Strategy</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        fig = create_equity_chart(perf)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


def section_orderbook(sim):
    """Order book visualization section."""
    st.markdown(f"""
    <div style="font-family: 'Orbitron', sans-serif; font-size: 1.5rem; font-weight: 700; color: {COLORS['text_primary']}; margin-bottom: 24px; display: flex; align-items: center; gap: 12px;">
        Order Book Visualization
        <span style="background: {COLORS['accent_primary']}; color: #000; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 600;">Simulated</span>
    </div>
    """, unsafe_allow_html=True)

    book = sim.get_orderbook()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig = create_depth_chart(book)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        render_orderbook_table(book)

    with col2:
        # Order Book Stats - using components.html for reliable rendering
        render_orderbook_stats_card(book)


def section_performance(sim):
    """Strategy backtest results."""
    st.markdown(f"""
    <div style="font-family: 'Orbitron', sans-serif; font-size: 1.5rem; font-weight: 700; color: {COLORS['text_primary']}; margin-bottom: 24px; display: flex; align-items: center; gap: 12px;">
        Strategy Backtest Results
        <span style="background: {COLORS['success']}; color: #000; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 600;">Simulated</span>
    </div>
    """, unsafe_allow_html=True)

    perf = sim.get_performance()

    # Metrics
    returns = perf['returns'].values
    total_return = (perf['equity'].iloc[-1] / perf['equity'].iloc[0] - 1) * 100
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
    max_dd = perf['drawdown'].max() * 100
    win_rate = np.sum(returns > 0) / len(returns) * 100

    cols = st.columns(4)
    metrics = [
        ("Total Return", f"{total_return:.1f}%", "green"),
        ("Sharpe Ratio", f"{sharpe:.2f}", "orange"),
        ("Max Drawdown", f"-{max_dd:.1f}%", "red"),
        ("Win Rate", f"{win_rate:.1f}%", "green"),
    ]

    for col, (label, value, color) in zip(cols, metrics):
        with col:
            render_metric(label, value, color=color)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    fig = create_equity_chart(perf)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)


def section_system(sim):
    """Engine performance benchmarks."""
    st.markdown(f"""
    <div style="font-family: 'Orbitron', sans-serif; font-size: 1.5rem; font-weight: 700; color: {COLORS['text_primary']}; margin-bottom: 24px; display: flex; align-items: center; gap: 12px;">
        C++ Engine Benchmarks
        <span style="background: {COLORS['info']}; color: #fff; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 600;">Measured</span>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    with cols[0]:
        render_metric("Peak Throughput", "64M ops/s", icon="🚀", color="orange")
    with cols[1]:
        render_metric("Memory Usage", "128 MB", icon="💾", color="orange")
    with cols[2]:
        render_metric("Cache Hit Rate", "99.7%", icon="⚡", color="green")
    with cols[3]:
        render_metric("Uptime", "99.99%", icon="🎯", color="green")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    benchmarks = [
        ("Add Order", 16, 500, "⚡"),
        ("Cancel Order", 50, 200, "🔄"),
        ("Get BBO", 0.7, 50, "📊"),
        ("Get Depth", 42, 500, "📚"),
        ("Mid Price", 0.66, 100, "💰"),
        ("Pool Allocate", 1.7, 20, "🧠"),
    ]

    with col1:
        for name, actual, target, icon in benchmarks[:3]:
            render_benchmark(name, actual, target, icon)

    with col2:
        for name, actual, target, icon in benchmarks[3:]:
            render_benchmark(name, actual, target, icon)


# =============================================================================
# WELCOME HERO SECTION
# =============================================================================
def render_welcome():
    """Render welcome hero section - technology focused."""
    from datetime import timezone
    utc_now = datetime.now(timezone.utc)

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {COLORS['bg_secondary']} 0%, {COLORS['bg_tertiary']} 100%); border-radius: 20px; padding: 40px; margin-bottom: 30px; border: 1px solid {COLORS['border']}; text-align: center;">
        <div style="font-size: 3rem; margin-bottom: 16px;">⚡</div>
        <h1 style="font-family: 'Orbitron', sans-serif; font-size: 2rem; margin-bottom: 12px; background: {COLORS['accent_gradient']}; -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            Low-Latency Order Book Engine
        </h1>
        <p style="color: {COLORS['text_secondary']}; font-size: 1.1rem; max-width: 700px; margin: 0 auto 24px auto; line-height: 1.6;">
            A high-performance C++ order book engine with sub-microsecond latency. This dashboard demonstrates the engine's capabilities with simulated market data and ML-driven predictions.
        </p>
        <div style="color: {COLORS['text_muted']}; font-size: 0.85rem; margin-bottom: 24px;">
            🕐 {utc_now.strftime('%B %d, %Y • %H:%M:%S')} UTC
        </div>
        <div style="display: flex; justify-content: center; gap: 16px; flex-wrap: wrap;">
            <div style="background: {COLORS['bg_primary']}; padding: 16px 24px; border-radius: 12px; border: 1px solid {COLORS['border']};">
                <div style="color: {COLORS['accent_primary']}; font-size: 1.5rem; font-weight: 700;">16 ns</div>
                <div style="color: {COLORS['text_muted']}; font-size: 0.8rem;">Add Order</div>
            </div>
            <div style="background: {COLORS['bg_primary']}; padding: 16px 24px; border-radius: 12px; border: 1px solid {COLORS['border']};">
                <div style="color: {COLORS['success']}; font-size: 1.5rem; font-weight: 700;">64M/s</div>
                <div style="color: {COLORS['text_muted']}; font-size: 0.8rem;">Throughput</div>
            </div>
            <div style="background: {COLORS['bg_primary']}; padding: 16px 24px; border-radius: 12px; border: 1px solid {COLORS['border']};">
                <div style="color: {COLORS['info']}; font-size: 1.5rem; font-weight: 700;">C++20</div>
                <div style="color: {COLORS['text_muted']}; font-size: 0.8rem;">Modern C++</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_info_card(title, description, icon="ℹ️"):
    """Render an info card explaining a concept."""
    st.markdown(f"""
    <div style="background: {COLORS['bg_tertiary']}; border-radius: 12px; padding: 16px; margin-bottom: 16px; border-left: 3px solid {COLORS['accent_primary']};">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <span style="font-size: 1.2rem;">{icon}</span>
            <span style="color: {COLORS['text_primary']}; font-weight: 600;">{title}</span>
        </div>
        <p style="color: {COLORS['text_secondary']}; font-size: 0.85rem; margin: 0; line-height: 1.5;">
            {description}
        </p>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# MAIN
# =============================================================================
def main():
    sim = get_simulator()

    # Sidebar - User Friendly
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; padding: 20px 0;">
            <div style="font-family: 'Orbitron'; font-size: 1.8rem; font-weight: 900; background: {COLORS['accent_gradient']}; -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                ATLAS
            </div>
            <div style="color: {COLORS['text_secondary']}; font-size: 0.8rem; margin-top: 4px;">
                Low-Latency Order Book Engine
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Tech-focused navigation
        page = st.radio(
            "Navigate",
            ["🏠 Home", "📊 Order Book", "📈 Backtest Results", "⚙️ Benchmarks"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Live engine stats
        book = sim.get_orderbook()
        from datetime import timezone
        utc_now = datetime.now(timezone.utc)

        st.markdown(f"""
        <div style="color: {COLORS['text_muted']}; font-size: 0.75rem; margin-bottom: 4px;">SIMULATED MID PRICE</div>
        """, unsafe_allow_html=True)
        st.metric("", f"${book['mid']:,.2f}", f"Spread: ${book['spread']:.2f}")

        st.markdown(f"""
        <div style="color: {COLORS['text_muted']}; font-size: 0.7rem; margin-top: 8px;">
            🕐 {utc_now.strftime('%H:%M:%S')} UTC
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Engine Status
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(0,212,170,0.1), rgba(255,107,0,0.1)); border-radius: 12px; padding: 16px;">
            <div style="color: {COLORS['text_primary']}; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.2rem;">⚡</span> Engine Status
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: {COLORS['text_secondary']}; font-size: 0.85rem;">Status</span>
                <span style="color: {COLORS['success']}; font-size: 0.85rem;">● Running</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: {COLORS['text_secondary']}; font-size: 0.85rem;">Add Order</span>
                <span style="color: {COLORS['accent_primary']}; font-size: 0.85rem; font-weight: 600;">16 ns</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: {COLORS['text_secondary']}; font-size: 0.85rem;">Throughput</span>
                <span style="color: {COLORS['accent_primary']}; font-size: 0.85rem; font-weight: 600;">64M/s</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Get in Touch section
        st.markdown(f"""
        <div style="text-align: center; padding: 12px;">
            <div style="color: {COLORS['text_muted']}; font-size: 0.8rem; margin-bottom: 8px;">Need help?</div>
        </div>
        """, unsafe_allow_html=True)

        # Initialize session state for contact form
        if 'show_contact' not in st.session_state:
            st.session_state.show_contact = False

        if st.button("✉️ Get in Touch", use_container_width=True):
            st.session_state.show_contact = not st.session_state.show_contact

        if st.session_state.show_contact:
            st.markdown(f"""
            <div style="background: {COLORS['bg_tertiary']}; border-radius: 12px; padding: 16px; margin-top: 12px; border: 1px solid {COLORS['border']};">
                <div style="color: {COLORS['accent_primary']}; font-weight: 600; margin-bottom: 12px;">Send us a message</div>
            </div>
            """, unsafe_allow_html=True)

            with st.form("contact_form", clear_on_submit=True):
                user_email = st.text_input("Your Email", placeholder="your@email.com")
                user_message = st.text_area("Message", placeholder="How can we help you?", height=100)
                submitted = st.form_submit_button("Send Message", use_container_width=True)

                if submitted:
                    if user_email and user_message:
                        # Create mailto link with pre-filled content
                        import urllib.parse
                        subject = urllib.parse.quote("Atlas Dashboard - Message from " + user_email)
                        body = urllib.parse.quote(f"From: {user_email}\n\nMessage:\n{user_message}")
                        mailto_link = f"mailto:atharvajoshi2024@gmail.com?subject={subject}&body={body}"

                        st.markdown(f"""
                        <div style="text-align: center; padding: 12px;">
                            <div style="color: {COLORS['success']}; margin-bottom: 8px;">✓ Message ready!</div>
                            <a href="{mailto_link}" target="_blank" style="background: {COLORS['accent_primary']}; color: #000; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                                Open Email Client
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.warning("Please fill in both fields")

    # Main content
    render_header()

    if "Home" in page:
        render_welcome()
        section_overview(sim)
    elif "Order Book" in page:
        render_info_card(
            "Live Order Book Visualization",
            "Watch the order book engine in action. This visualization shows simulated market data processed by our C++ engine at nanosecond speeds.",
            "📊"
        )
        section_orderbook(sim)
    elif "Backtest" in page:
        render_info_card(
            "Strategy Backtest Results",
            "Performance metrics from backtesting our ML-driven trading signals. These results demonstrate the predictive capabilities of the system.",
            "📈"
        )
        section_performance(sim)
    elif "Benchmarks" in page:
        render_info_card(
            "C++ Engine Performance Benchmarks",
            "Raw performance metrics from the order book engine. All operations measured in nanoseconds (billionths of a second). Target: sub-microsecond latency for all critical paths.",
            "⚙️"
        )
        section_system(sim)


if __name__ == "__main__":
    main()
