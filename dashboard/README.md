---
title: Atlas Trading Dashboard
emoji: 📈
colorFrom: orange
colorTo: amber
sdk: streamlit
sdk_version: 1.28.0
app_file: app.py
pinned: true
license: mit
---

# Atlas: Low-Latency Order Book Engine

Premium animated trading dashboard with TradingView-inspired UI for the Atlas quantitative trading system.

## Features

- **Interactive Candlestick Charts**: Real-time OHLC with volume overlay
- **Trading Panel**: Buy/Sell tabs, order types, percentage buttons
- **AI Prediction Badges**: ML-driven market direction indicators
- **Order Book Depth**: Live bid/ask visualization with depth bars
- **Performance Analytics**: Equity curves, drawdown, rolling Sharpe
- **System Metrics**: Sub-microsecond latency benchmarks (16ns order add)
- **Backtest Lab**: Interactive strategy simulation

## Design

- Orange/Amber color scheme with glassmorphism effects
- 15+ CSS animations (slide-up, fade-in, pulse-glow, shimmer)
- Animated particle background
- Dark theme inspired by TradingView and Bloomberg

## Tech Stack

- C++ order book engine with 16ns latency
- Python ML pipeline with Numba JIT
- Streamlit + Plotly for visualization
- Responsive design with smooth animations

## Links

- [GitHub Repository](https://github.com/atharvajoshi01/Atlas)
