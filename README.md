<p align="center">
  <h1 align="center">Atlas</h1>
  <p align="center"><strong>Sub-Nanosecond Order Book Engine in C++20</strong></p>
</p>

<p align="center">
  <a href="https://github.com/atharvajoshi01/Atlas/actions/workflows/ci.yml">
    <img src="https://github.com/atharvajoshi01/Atlas/actions/workflows/ci.yml/badge.svg" alt="CI"/>
  </a>
  <img src="https://img.shields.io/badge/C%2B%2B-20-blue?logo=cplusplus" alt="C++20"/>
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Add%20Order-16%20ns-orange?style=for-the-badge" alt="Add Order: 16ns"/>
  <img src="https://img.shields.io/badge/Get%20BBO-0.7%20ns-green?style=for-the-badge" alt="Get BBO: 0.7ns"/>
  <img src="https://img.shields.io/badge/Throughput-62M%20ops%2Fs-blue?style=for-the-badge" alt="Throughput: 62M ops/s"/>
</p>

---

A production-grade limit order book engine achieving **sub-20 nanosecond** order insertion with zero heap allocations in the hot path. Built for HFT research and quantitative trading systems.

## Benchmark Results (Apple M1 Pro)

```
BM_OrderBook_AddOrder          16.3 ns    62M ops/s    ← Core operation
BM_OrderBook_CancelOrder       50.8 ns    20M ops/s
BM_OrderBook_GetBBO             0.72 ns   1.4B ops/s   ← Sub-nanosecond
BM_OrderBook_BestBid            0.28 ns   3.5B ops/s
BM_OrderBook_MidPrice           0.67 ns   1.5B ops/s
BM_OrderBook_GetDepth/10       41.0 ns    24M ops/s
BM_PoolAllocator_Allocate       1.7 ns   588M ops/s
BM_RingBuffer_PushPop           3.2 ns   620M ops/s
BM_MatchingEngine_Cancel        2.8 ns   354M ops/s
```

> Run `./build/atlas_benchmarks` to reproduce. Full results in [`docs/benchmark_results.txt`](docs/benchmark_results.txt)

## Quick Start

```bash
git clone https://github.com/atharvajoshi01/Atlas.git
cd Atlas

# Build (requires CMake 3.16+, C++20 compiler)
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)

# Run benchmarks
./atlas_benchmarks

# Run tests
./atlas_tests
```

## Architecture

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                     ATLAS ENGINE                            │
                    └─────────────────────────────────────────────────────────────┘
                                              │
            ┌─────────────────────────────────┼─────────────────────────────────┐
            │                                 │                                 │
            ▼                                 ▼                                 ▼
    ┌───────────────┐                ┌───────────────┐                ┌───────────────┐
    │  MARKET DATA  │                │  ORDER BOOK   │                │   MATCHING    │
    │    HANDLER    │                │    (CORE)     │                │    ENGINE     │
    ├───────────────┤                ├───────────────┤                ├───────────────┤
    │ Ring Buffer   │ ──────────────▶│ Price Levels  │◀──────────────▶│ Price-Time    │
    │ (SPSC, 3ns)   │                │ (std::map)    │                │ Priority      │
    │               │                │               │                │               │
    │ ITCH Parser   │                │ Order Index   │                │ IOC/FOK/GTC   │
    │ (0.8ns/msg)   │                │ (hash map)    │                │ Support       │
    │               │                │               │                │               │
    │ Feed Handler  │                │ BBO Cache     │                │ Trade         │
    │ Interface     │                │ (0.7ns)       │                │ Callbacks     │
    └───────────────┘                └───────────────┘                └───────────────┘
            │                                 │                                 │
            └─────────────────────────────────┼─────────────────────────────────┘
                                              │
                                              ▼
                                    ┌───────────────┐
                                    │ MEMORY POOL   │
                                    ├───────────────┤
                                    │ 64-byte align │
                                    │ Zero malloc   │
                                    │ 1.7ns alloc   │
                                    └───────────────┘
```

## Core Components

### Order Book (`include/atlas/core/order_book.hpp`)

The heart of the engine. Maintains bid/ask sides with price-time priority.

```cpp
#include "atlas/core/order_book.hpp"

atlas::OrderBook book;

// Add orders - 16ns per operation
book.add_order(/*id=*/1, /*price=*/to_price(100.00), /*qty=*/100, Side::Buy);
book.add_order(/*id=*/2, /*price=*/to_price(100.01), /*qty=*/50,  Side::Sell);

// Get BBO - 0.7ns (cached)
auto bbo = book.get_bbo();
std::cout << "Spread: " << from_price(bbo.spread()) << std::endl;

// Get market depth
std::vector<DepthLevel> bids, asks;
book.get_depth(bids, asks, /*levels=*/10);  // 41ns for 10 levels
```

**Design decisions:**
- `std::map` for price levels - O(log N) with N < 100 typical levels
- Intrusive doubly-linked list for orders at each level - O(1) cancel
- Cached BBO invalidated only on best-level changes

### Memory Pool (`include/atlas/memory/pool_allocator.hpp`)

Zero-allocation order management via pre-allocated memory pool.

```cpp
#include "atlas/memory/pool_allocator.hpp"

// Pre-allocate 1M order slots, 64-byte aligned
atlas::PoolAllocator<Order, 1000000> pool;

Order* order = pool.allocate();   // 1.7ns - no syscall
pool.deallocate(order);           // O(1) return to free list
```

**Why it matters:** `new`/`delete` costs ~25ns+ with potential syscalls. Pool allocation is 15x faster and deterministic.

### Ring Buffer (`include/atlas/feed/ring_buffer.hpp`)

Lock-free SPSC queue for market data ingestion.

```cpp
#include "atlas/feed/ring_buffer.hpp"

atlas::RingBuffer<MarketMessage, 65536> buffer;  // Power of 2 for fast modulo

// Producer (market data thread)
buffer.push(message);  // 3.2ns

// Consumer (order book thread)
MarketMessage msg;
if (buffer.pop(msg)) { /* process */ }
```

### Matching Engine (`include/atlas/matching/matching_engine.hpp`)

Full matching with IOC, FOK, GTC order types.

```cpp
#include "atlas/matching/matching_engine.hpp"

atlas::MatchingEngine engine;

// Register trade callback
engine.set_trade_callback([](const Trade& trade) {
    std::cout << "Trade: " << trade.quantity << " @ " << trade.price << "\n";
});

// Submit order - matches immediately if crosses spread
engine.submit_order(order);
```

## Project Structure

```
Atlas/
├── include/atlas/
│   ├── core/
│   │   ├── types.hpp          # Price, Quantity, OrderId (64-byte aligned)
│   │   ├── order.hpp          # Order struct with intrusive list pointers
│   │   ├── price_level.hpp    # Doubly-linked order list at price
│   │   └── order_book.hpp     # Main order book class
│   ├── memory/
│   │   └── pool_allocator.hpp # Lock-free memory pool
│   ├── matching/
│   │   └── matching_engine.hpp # Price-time priority matching
│   └── feed/
│       ├── ring_buffer.hpp    # SPSC lock-free queue
│       ├── market_data.hpp    # Message definitions
│       └── feed_handler.hpp   # Feed handler interface
├── tests/cpp/
│   ├── test_order_book.cpp
│   ├── test_matching_engine.cpp
│   ├── test_ring_buffer.cpp
│   └── benchmark/
│       ├── bench_order_book.cpp
│       └── bench_matching.cpp
├── atlas/                     # Python ML pipeline
│   ├── features/              # 50+ order book features (Numba JIT)
│   ├── signals/               # Alpha generation
│   └── backtest/              # Execution simulation
└── dashboard/                 # Streamlit visualization
```

## Performance Techniques

| Technique | Impact | Location |
|-----------|--------|----------|
| **Cache-line alignment** | Prevents false sharing | `types.hpp` - 64-byte aligned structs |
| **Memory pooling** | Zero malloc in hot path | `pool_allocator.hpp` |
| **BBO caching** | 0.7ns best price access | `order_book.hpp` |
| **Intrusive lists** | O(1) order removal | `price_level.hpp` |
| **Power-of-2 sizing** | Fast modulo via bitmask | `ring_buffer.hpp` |
| **Branch prediction hints** | `[[likely]]`/`[[unlikely]]` | Throughout |

## Python Integration

The C++ engine exposes Python bindings for research:

```python
from atlas import OrderBook, Side, to_price

book = OrderBook()
book.add_order(id=1, price=to_price(100.0), quantity=100, side=Side.Buy)

# Get depth as NumPy array (zero-copy)
depth = book.get_depth_array(levels=10)  # Shape: (10, 4)
```

### Feature Engineering

```python
from atlas.features import FeaturePipeline

pipeline = FeaturePipeline.default()  # 50+ features
features = pipeline.compute(order_book_state)  # < 1ms
```

### Backtesting

```python
from atlas.backtest import BacktestEngine

engine = BacktestEngine(initial_capital=100000)
result = engine.run(strategy, market_data)

print(f"Sharpe: {result.sharpe_ratio:.2f}")
print(f"Max DD: {result.max_drawdown:.2%}")
```

## Requirements

- **C++20** compiler (GCC 10+, Clang 12+, MSVC 2019+)
- **CMake** 3.16+
- **Google Benchmark** (fetched automatically)
- **Google Test** (fetched automatically)
- **Python 3.8+** (optional, for ML pipeline)

## References

- Harris, L. (2003). *Trading and Exchanges*
- Cartea, A., et al. (2015). *Algorithmic and High-Frequency Trading*

## Live Demo

Interactive dashboard: [**atlas-dashboard.hf.space**](https://huggingface.co/spaces/aadu21/atlas-dashboard)

## Author

**Atharva Joshi** - [GitHub](https://github.com/atharvajoshi01) | [LinkedIn](https://linkedin.com/in/atharvajoshi01)

## License

MIT
