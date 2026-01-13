"""Atlas: Low-Latency Order Book Engine with Predictive Execution.

This package provides:
- High-performance order book and matching engine (C++ with Python bindings)
- Feature engineering for order book data (Numba-optimized)
- Alpha signal generation and validation
- Backtest engine with realistic execution simulation
- Monitoring and observability tools
"""

__version__ = "0.1.0"
__author__ = "Atlas Team"

# Try to import C++ bindings
try:
    from atlas._atlas import (
        # Core types
        Side,
        OrderType,
        OrderStatus,
        # Price utilities
        to_price,
        from_price,
        PRICE_MULTIPLIER,
        INVALID_PRICE,
        INVALID_ORDER_ID,
        # Order and Trade
        Order,
        Trade,
        BBO,
        DepthLevel,
        ExecutionResult,
        # Order Book
        OrderBook,
        # Matching Engine
        MatchingEngine,
        MatchingEngineConfig,
        # Feed Handler
        L2Message,
        FeedStats,
        FeedHandler,
    )
    _HAS_CPP_BINDINGS = True
except ImportError:
    _HAS_CPP_BINDINGS = False
    import warnings
    warnings.warn(
        "C++ bindings not available. Build with CMake to enable full functionality.",
        ImportWarning
    )

# Python-only imports always available
from atlas.features import (
    FeatureGenerator,
    OrderBookFeatures,
    TradeFeatures,
    VolatilityFeatures,
    MicrostructureFeatures,
    FeaturePipeline,
)

from atlas.signals import (
    AlphaSignal,
    WalkForwardValidator,
)

from atlas.backtest import (
    Strategy,
    BacktestEngine,
    BacktestConfig,
    BacktestResult,
)

__all__ = [
    # Version
    "__version__",
    # C++ bindings
    "Side",
    "OrderType",
    "OrderStatus",
    "to_price",
    "from_price",
    "PRICE_MULTIPLIER",
    "INVALID_PRICE",
    "INVALID_ORDER_ID",
    "Order",
    "Trade",
    "BBO",
    "DepthLevel",
    "ExecutionResult",
    "OrderBook",
    "MatchingEngine",
    "MatchingEngineConfig",
    "L2Message",
    "FeedStats",
    "FeedHandler",
    # Features
    "FeatureGenerator",
    "OrderBookFeatures",
    "TradeFeatures",
    "VolatilityFeatures",
    "MicrostructureFeatures",
    "FeaturePipeline",
    # Signals
    "AlphaSignal",
    "WalkForwardValidator",
    # Backtest
    "Strategy",
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResult",
]
