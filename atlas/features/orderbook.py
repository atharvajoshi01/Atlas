"""Order book feature computation with Numba optimization."""

from typing import Any
import numpy as np

try:
    import numba
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    # Fallback decorator that does nothing
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from atlas.features.base import FeatureGenerator


# =============================================================================
# Numba-optimized computation functions
# =============================================================================

@jit(nopython=True, cache=True)
def compute_mid_price(best_bid: float, best_ask: float) -> float:
    """Compute mid price."""
    if best_bid <= 0 or best_ask <= 0:
        return np.nan
    return (best_bid + best_ask) / 2.0


@jit(nopython=True, cache=True)
def compute_spread_bps(best_bid: float, best_ask: float) -> float:
    """Compute bid-ask spread in basis points."""
    if best_bid <= 0 or best_ask <= 0:
        return np.nan
    mid = (best_bid + best_ask) / 2.0
    return (best_ask - best_bid) / mid * 10000.0


@jit(nopython=True, cache=True)
def compute_weighted_mid(
    best_bid: float,
    best_ask: float,
    bid_qty: float,
    ask_qty: float
) -> float:
    """Compute quantity-weighted mid price."""
    if bid_qty <= 0 and ask_qty <= 0:
        return np.nan
    if bid_qty <= 0:
        return best_ask
    if ask_qty <= 0:
        return best_bid
    total_qty = bid_qty + ask_qty
    return (bid_qty * best_ask + ask_qty * best_bid) / total_qty


@jit(nopython=True, cache=True)
def compute_imbalance(
    bid_sizes: np.ndarray,
    ask_sizes: np.ndarray,
    levels: int = 5
) -> float:
    """Compute order book imbalance for top N levels.

    Imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)
    Range: [-1, 1] where 1 = all bids, -1 = all asks
    """
    bid_vol = 0.0
    ask_vol = 0.0

    for i in range(min(levels, len(bid_sizes))):
        bid_vol += bid_sizes[i]

    for i in range(min(levels, len(ask_sizes))):
        ask_vol += ask_sizes[i]

    total = bid_vol + ask_vol
    if total < 1e-10:
        return 0.0

    return (bid_vol - ask_vol) / total


@jit(nopython=True, cache=True)
def compute_weighted_imbalance(
    bid_prices: np.ndarray,
    bid_sizes: np.ndarray,
    ask_prices: np.ndarray,
    ask_sizes: np.ndarray,
    levels: int = 10
) -> float:
    """Compute distance-weighted order book imbalance.

    Weights decrease with distance from mid price.
    """
    if len(bid_prices) == 0 or len(ask_prices) == 0:
        return 0.0

    mid = (bid_prices[0] + ask_prices[0]) / 2.0

    bid_weighted = 0.0
    ask_weighted = 0.0

    for i in range(min(levels, len(bid_prices))):
        dist = abs(mid - bid_prices[i])
        weight = 1.0 / (1.0 + dist)
        bid_weighted += bid_sizes[i] * weight

    for i in range(min(levels, len(ask_prices))):
        dist = abs(mid - ask_prices[i])
        weight = 1.0 / (1.0 + dist)
        ask_weighted += ask_sizes[i] * weight

    total = bid_weighted + ask_weighted
    if total < 1e-10:
        return 0.0

    return (bid_weighted - ask_weighted) / total


@jit(nopython=True, cache=True)
def compute_book_pressure(
    bid_prices: np.ndarray,
    bid_sizes: np.ndarray,
    ask_prices: np.ndarray,
    ask_sizes: np.ndarray,
    levels: int = 10
) -> float:
    """Compute order book pressure.

    Pressure = Σ(qty_i / distance_i) for bids - same for asks
    Positive = more buy pressure, negative = more sell pressure
    """
    if len(bid_prices) == 0 or len(ask_prices) == 0:
        return 0.0

    mid = (bid_prices[0] + ask_prices[0]) / 2.0

    bid_pressure = 0.0
    ask_pressure = 0.0

    for i in range(min(levels, len(bid_prices))):
        dist = max(mid - bid_prices[i], 1e-6)
        bid_pressure += bid_sizes[i] / dist

    for i in range(min(levels, len(ask_prices))):
        dist = max(ask_prices[i] - mid, 1e-6)
        ask_pressure += ask_sizes[i] / dist

    return bid_pressure - ask_pressure


@jit(nopython=True, cache=True)
def compute_depth_ratio(
    bid_sizes: np.ndarray,
    ask_sizes: np.ndarray,
    levels: int = 20
) -> float:
    """Compute ratio of total bid to ask volume.

    Range: (0, inf) where >1 = more bids, <1 = more asks
    """
    bid_vol = 0.0
    ask_vol = 0.0

    for i in range(min(levels, len(bid_sizes))):
        bid_vol += bid_sizes[i]

    for i in range(min(levels, len(ask_sizes))):
        ask_vol += ask_sizes[i]

    if ask_vol < 1e-10:
        return np.nan

    return bid_vol / ask_vol


@jit(nopython=True, cache=True)
def compute_price_impact(
    prices: np.ndarray,
    sizes: np.ndarray,
    target_qty: float
) -> float:
    """Compute price impact for walking through the book.

    Returns impact in basis points from best price.
    """
    if len(prices) == 0:
        return np.nan

    remaining = target_qty
    weighted_price = 0.0
    total_filled = 0.0

    for i in range(len(prices)):
        fill = min(remaining, sizes[i])
        weighted_price += fill * prices[i]
        total_filled += fill
        remaining -= fill
        if remaining <= 0:
            break

    if total_filled < 1e-10:
        return np.nan

    vwap = weighted_price / total_filled
    impact_bps = (vwap - prices[0]) / prices[0] * 10000.0
    return abs(impact_bps)


@jit(nopython=True, cache=True)
def compute_order_flow_imbalance(
    bid_changes: np.ndarray,
    ask_changes: np.ndarray,
    window: int = 100
) -> float:
    """Compute order flow imbalance from level changes.

    OFI = Σ(bid_changes) - Σ(ask_changes) over window
    """
    n = min(window, len(bid_changes), len(ask_changes))
    if n == 0:
        return 0.0

    bid_sum = 0.0
    ask_sum = 0.0

    for i in range(n):
        bid_sum += bid_changes[-(i+1)]
        ask_sum += ask_changes[-(i+1)]

    return bid_sum - ask_sum


# =============================================================================
# OrderBookFeatures class
# =============================================================================

class OrderBookFeatures(FeatureGenerator):
    """Order book derived features.

    Computes features from the current state of the limit order book:
    - Mid price, spread
    - Book imbalance at various depth levels
    - Weighted imbalance (distance-weighted)
    - Book pressure
    - Depth ratios
    - Price impact for hypothetical orders
    """

    FEATURE_NAMES = [
        "mid_price",
        "spread_bps",
        "weighted_mid",
        "imbalance_1",      # Top of book
        "imbalance_5",      # Top 5 levels
        "imbalance_10",     # Top 10 levels
        "weighted_imbalance",
        "book_pressure",
        "depth_ratio",
        "bid_depth_5",
        "ask_depth_5",
        "bid_depth_10",
        "ask_depth_10",
        "price_impact_bid_100",
        "price_impact_ask_100",
        "price_impact_bid_1000",
        "price_impact_ask_1000",
    ]

    def __init__(
        self,
        lookback_window: int = 100,
        update_frequency: int = 1,
        impact_sizes: list[float] | None = None,
    ):
        """Initialize OrderBookFeatures.

        Args:
            lookback_window: Window for rolling calculations.
            update_frequency: Compute features every N updates.
            impact_sizes: Order sizes for price impact calculation.
        """
        super().__init__(lookback_window, update_frequency)
        self.impact_sizes = impact_sizes or [100.0, 1000.0]

    @property
    def feature_names(self) -> list[str]:
        return self.FEATURE_NAMES

    def compute(self, state: dict[str, Any]) -> np.ndarray:
        """Compute all order book features.

        Args:
            state: Dictionary with keys:
                - bid_prices: np.ndarray of bid prices (best first)
                - bid_sizes: np.ndarray of bid quantities
                - ask_prices: np.ndarray of ask prices (best first)
                - ask_sizes: np.ndarray of ask quantities

        Returns:
            numpy array of feature values.
        """
        features = np.zeros(len(self.FEATURE_NAMES), dtype=np.float64)

        bid_prices = np.asarray(state.get("bid_prices", []), dtype=np.float64)
        bid_sizes = np.asarray(state.get("bid_sizes", []), dtype=np.float64)
        ask_prices = np.asarray(state.get("ask_prices", []), dtype=np.float64)
        ask_sizes = np.asarray(state.get("ask_sizes", []), dtype=np.float64)

        # Check for empty book
        if len(bid_prices) == 0 or len(ask_prices) == 0:
            features[:] = np.nan
            return features

        best_bid = bid_prices[0]
        best_ask = ask_prices[0]
        bid_qty = bid_sizes[0] if len(bid_sizes) > 0 else 0.0
        ask_qty = ask_sizes[0] if len(ask_sizes) > 0 else 0.0

        # Basic price features
        features[0] = compute_mid_price(best_bid, best_ask)
        features[1] = compute_spread_bps(best_bid, best_ask)
        features[2] = compute_weighted_mid(best_bid, best_ask, bid_qty, ask_qty)

        # Imbalance features
        features[3] = compute_imbalance(bid_sizes, ask_sizes, 1)
        features[4] = compute_imbalance(bid_sizes, ask_sizes, 5)
        features[5] = compute_imbalance(bid_sizes, ask_sizes, 10)
        features[6] = compute_weighted_imbalance(
            bid_prices, bid_sizes, ask_prices, ask_sizes
        )

        # Book pressure
        features[7] = compute_book_pressure(
            bid_prices, bid_sizes, ask_prices, ask_sizes
        )

        # Depth ratio
        features[8] = compute_depth_ratio(bid_sizes, ask_sizes)

        # Total depth at levels
        features[9] = np.sum(bid_sizes[:5]) if len(bid_sizes) >= 5 else np.sum(bid_sizes)
        features[10] = np.sum(ask_sizes[:5]) if len(ask_sizes) >= 5 else np.sum(ask_sizes)
        features[11] = np.sum(bid_sizes[:10]) if len(bid_sizes) >= 10 else np.sum(bid_sizes)
        features[12] = np.sum(ask_sizes[:10]) if len(ask_sizes) >= 10 else np.sum(ask_sizes)

        # Price impact
        features[13] = compute_price_impact(bid_prices, bid_sizes, 100)
        features[14] = compute_price_impact(ask_prices, ask_sizes, 100)
        features[15] = compute_price_impact(bid_prices, bid_sizes, 1000)
        features[16] = compute_price_impact(ask_prices, ask_sizes, 1000)

        return features
