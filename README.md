# Atlas: Low-Latency Order Book Engine with Predictive Execution

A production-grade limit order book engine in C++ with sub-microsecond performance, integrated with a Python ML pipeline for short-term price prediction and smart order execution.

## Features

### C++ Core Engine
- **Sub-microsecond latency**: Order add < 500ns, cancel < 200ns (p99)
- **Zero malloc in hot path**: Custom memory pool allocator
- **Cache-optimized**: 64-byte aligned structures
- **Lock-free SPSC ring buffer**: For market data processing
- **Full matching engine**: Price-time priority with IOC/FOK support

### Python Research Pipeline
- **Feature engineering**: 50+ order book and trade features with Numba JIT
- **Alpha signal generation**: Walk-forward validated ML models
- **Backtest engine**: Realistic execution with market impact modeling
- **Monitoring**: PSI drift detection, model performance tracking

## Performance Benchmarks

### Order Book Engine (C++)
| Operation        | Latency  | Target   | Status |
|------------------|----------|----------|--------|
| Add Order        | ~16 ns   | < 500 ns | ✅ 31x faster |
| Cancel Order     | ~50 ns   | < 200 ns | ✅ 4x faster |
| Get BBO          | ~0.7 ns  | < 50 ns  | ✅ 71x faster |
| Get Depth (10)   | ~42 ns   | < 500 ns | ✅ 12x faster |
| Mid Price        | ~0.66 ns | < 100 ns | ✅ 151x faster |
| Pool Allocate    | ~1.7 ns  | < 20 ns  | ✅ 12x faster |

### Feature Engine (Python)
| Operation           | Latency |
|---------------------|---------|
| Full feature vector | < 1 ms  |
| Incremental update  | < 100 us|

## Quick Start

### Build C++ Components

```bash
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)

# Run tests
ctest --verbose

# Run benchmarks
./atlas_benchmarks
```

### Install Python Package

```bash
pip install -e ".[all]"
```

### Basic Usage

```python
from atlas import OrderBook, Side, to_price, from_price

# Create order book
book = OrderBook()

# Add orders
book.add_order(id=1, price=to_price(100.0), quantity=100, side=Side.Buy)
book.add_order(id=2, price=to_price(100.01), quantity=50, side=Side.Sell)

# Get BBO
bbo = book.get_bbo()
print(f"Bid: {from_price(bbo.bid_price)} x {bbo.bid_quantity}")
print(f"Ask: {from_price(bbo.ask_price)} x {bbo.ask_quantity}")

# Get depth as NumPy array
depth = book.get_depth_array(levels=10)
print(f"Depth shape: {depth.shape}")  # (10, 4)
```

### Feature Engineering

```python
from atlas.features import FeaturePipeline

# Create default pipeline
pipeline = FeaturePipeline.default()

# Compute features from market state
state = {
    "bid_prices": bid_prices,
    "bid_sizes": bid_sizes,
    "ask_prices": ask_prices,
    "ask_sizes": ask_sizes,
}
features = pipeline.compute_normalized(state)
```

### Backtest

```python
from atlas.backtest import BacktestEngine, BacktestConfig
from atlas.backtest.strategy import SimpleStrategy

# Configure backtest
config = BacktestConfig(
    initial_capital=100000,
    commission_per_share=0.001,
    slippage_bps=1.0,
)

# Run backtest
engine = BacktestEngine(config)
strategy = SimpleStrategy(imbalance_threshold=0.3)
result = engine.run(strategy, market_data, features)

print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
print(f"Max Drawdown: {result.max_drawdown:.2%}")
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Market Data   │────▶│   Order Book    │────▶│    Features     │
│    Handler      │     │    (C++)        │     │   (Python)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Execution    │◀────│    Signal       │◀────│  Alpha Model    │
│   Simulator     │     │   Generator     │     │    (ML)         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Project Structure

```
atlas/
├── include/atlas/       # C++ headers
│   ├── core/            # Order, PriceLevel, OrderBook
│   ├── memory/          # Pool allocator
│   ├── matching/        # Matching engine
│   └── feed/            # Ring buffer, feed handler
├── src/                 # C++ implementation
├── tests/cpp/           # C++ tests and benchmarks
├── atlas/               # Python package
│   ├── features/        # Feature engineering
│   ├── signals/         # Alpha generation
│   ├── backtest/        # Backtesting
│   └── monitoring/      # Drift detection
└── dashboard/           # Streamlit dashboard
```

## Design Decisions

### Why std::map for price levels?
- O(log N) lookup with N = number of price levels (typically < 100)
- Natural ordering for bid/ask sides
- Considered flat_map but insertion overhead dominates for active books

### Why intrusive linked lists for orders?
- O(1) order removal with direct pointer access
- No memory allocation for list nodes
- Cache-friendly traversal for matching

### Why Numba for Python features?
- Near-C++ performance for numerical code
- Faster iteration than pure C++ during research phase
- Easy fallback to NumPy for unsupported operations

### Why walk-forward validation?
- Temporal data requires temporal splits
- Prevents look-ahead bias
- More realistic evaluation of live performance

## References

- Harris, L. (2003). Trading and Exchanges
- Cartea, A., et al. (2015). Algorithmic and High-Frequency Trading
- Almgren, R., & Chriss, N. (2001). Optimal Execution of Portfolio Transactions

## Dashboard

The project includes a Streamlit dashboard for real-time visualization:

```bash
# Install dashboard dependencies
pip install -e ".[dashboard]"

# Run locally
streamlit run dashboard/app.py
```

### Deploy to Streamlit Cloud
1. Fork/push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select this repository and `dashboard/app.py` as the main file
5. Deploy

## Author

**Atharva Joshi** - [GitHub](https://github.com/atharvajoshi01)

## License

MIT
