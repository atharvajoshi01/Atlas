---
title: Atlas Trading Dashboard
emoji: 📈
colorFrom: cyan
colorTo: indigo
sdk: streamlit
sdk_version: 1.28.0
app_file: app.py
pinned: true
license: mit
---

# Atlas: Low-Latency Order Book Engine

Premium trading dashboard with real-time visualization for the Atlas quantitative trading system.

## Features

- **Real-time Order Book**: Live depth visualization and heatmaps
- **Performance Analytics**: Equity curves, drawdown, rolling Sharpe
- **Alpha Signals**: ML-based signal monitoring and feature importance
- **System Metrics**: Sub-microsecond latency benchmarks (16ns order add)
- **Backtest Lab**: Interactive strategy simulation

## Tech Stack

- C++ order book engine with 16ns latency
- Python ML pipeline with Numba JIT
- Streamlit + Plotly for visualization
- Dark theme inspired by Bloomberg/TradingView

## Links

- [GitHub Repository](https://github.com/atharvajoshi01/Atlas)
