"""Trade-based feature computation."""

from typing import Any
import numpy as np

try:
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from atlas.features.base import FeatureGenerator


@jit(nopython=True, cache=True)
def compute_trade_imbalance(
    trade_sides: np.ndarray,
    trade_sizes: np.ndarray,
    window: int = 100
) -> float:
    """Compute trade imbalance.

    Imbalance = (buy_vol - sell_vol) / total_vol
    Trade sides: 1 = buy (aggressor), -1 = sell (aggressor)
    """
    n = min(window, len(trade_sides))
    if n == 0:
        return 0.0

    buy_vol = 0.0
    sell_vol = 0.0

    for i in range(n):
        idx = len(trade_sides) - 1 - i
        if trade_sides[idx] > 0:
            buy_vol += trade_sizes[idx]
        else:
            sell_vol += trade_sizes[idx]

    total = buy_vol + sell_vol
    if total < 1e-10:
        return 0.0

    return (buy_vol - sell_vol) / total


@jit(nopython=True, cache=True)
def compute_signed_volume(
    trade_sides: np.ndarray,
    trade_sizes: np.ndarray,
    window: int = 100
) -> float:
    """Compute net signed volume."""
    n = min(window, len(trade_sides))
    if n == 0:
        return 0.0

    signed_vol = 0.0
    for i in range(n):
        idx = len(trade_sides) - 1 - i
        signed_vol += trade_sides[idx] * trade_sizes[idx]

    return signed_vol


@jit(nopython=True, cache=True)
def compute_vwap(
    trade_prices: np.ndarray,
    trade_sizes: np.ndarray,
    window: int = 100
) -> float:
    """Compute volume-weighted average price."""
    n = min(window, len(trade_prices))
    if n == 0:
        return np.nan

    total_value = 0.0
    total_volume = 0.0

    for i in range(n):
        idx = len(trade_prices) - 1 - i
        total_value += trade_prices[idx] * trade_sizes[idx]
        total_volume += trade_sizes[idx]

    if total_volume < 1e-10:
        return np.nan

    return total_value / total_volume


@jit(nopython=True, cache=True)
def compute_vwap_deviation(
    last_price: float,
    trade_prices: np.ndarray,
    trade_sizes: np.ndarray,
    window: int = 100
) -> float:
    """Compute deviation of last price from VWAP in bps."""
    vwap = compute_vwap(trade_prices, trade_sizes, window)
    if np.isnan(vwap) or vwap < 1e-10:
        return np.nan
    return (last_price - vwap) / vwap * 10000.0


@jit(nopython=True, cache=True)
def compute_trade_flow_toxicity(
    trade_sides: np.ndarray,
    trade_sizes: np.ndarray,
    window: int = 100
) -> float:
    """Compute trade flow toxicity (VPIN-like metric).

    Toxicity = |net_signed_volume| / total_volume
    High values indicate informed trading.
    """
    n = min(window, len(trade_sides))
    if n == 0:
        return 0.0

    signed_vol = 0.0
    total_vol = 0.0

    for i in range(n):
        idx = len(trade_sides) - 1 - i
        signed_vol += trade_sides[idx] * trade_sizes[idx]
        total_vol += trade_sizes[idx]

    if total_vol < 1e-10:
        return 0.0

    return abs(signed_vol) / total_vol


@jit(nopython=True, cache=True)
def compute_trade_arrival_rate(
    trade_times: np.ndarray,
    window_ns: int = 1_000_000_000  # 1 second in nanoseconds
) -> float:
    """Compute trade arrival rate (trades per second)."""
    if len(trade_times) < 2:
        return 0.0

    # Find trades within the window
    latest_time = trade_times[-1]
    cutoff_time = latest_time - window_ns

    count = 0
    for i in range(len(trade_times) - 1, -1, -1):
        if trade_times[i] >= cutoff_time:
            count += 1
        else:
            break

    duration_sec = window_ns / 1e9
    return count / duration_sec


@jit(nopython=True, cache=True)
def compute_trade_size_std(
    trade_sizes: np.ndarray,
    window: int = 100
) -> float:
    """Compute standard deviation of trade sizes."""
    n = min(window, len(trade_sizes))
    if n < 2:
        return np.nan

    mean = 0.0
    for i in range(n):
        idx = len(trade_sizes) - 1 - i
        mean += trade_sizes[idx]
    mean /= n

    var = 0.0
    for i in range(n):
        idx = len(trade_sizes) - 1 - i
        var += (trade_sizes[idx] - mean) ** 2
    var /= (n - 1)

    return np.sqrt(var)


class TradeFeatures(FeatureGenerator):
    """Trade-based features.

    Computes features from trade tick data:
    - Trade imbalance
    - Signed volume
    - VWAP and deviation
    - Trade flow toxicity
    - Arrival rate
    - Trade size statistics
    """

    FEATURE_NAMES = [
        "trade_imbalance_100",
        "trade_imbalance_500",
        "signed_volume_100",
        "signed_volume_500",
        "vwap_100",
        "vwap_500",
        "vwap_deviation_100",
        "vwap_deviation_500",
        "flow_toxicity_100",
        "flow_toxicity_500",
        "trade_count_1s",
        "trade_rate_1s",
        "avg_trade_size_100",
        "trade_size_std_100",
        "last_trade_side",
        "last_trade_size",
    ]

    @property
    def feature_names(self) -> list[str]:
        return self.FEATURE_NAMES

    def compute(self, state: dict[str, Any]) -> np.ndarray:
        """Compute all trade features.

        Args:
            state: Dictionary with keys:
                - trade_prices: np.ndarray of trade prices
                - trade_sizes: np.ndarray of trade quantities
                - trade_sides: np.ndarray of trade sides (1=buy, -1=sell)
                - trade_times: np.ndarray of trade timestamps (nanoseconds)

        Returns:
            numpy array of feature values.
        """
        features = np.zeros(len(self.FEATURE_NAMES), dtype=np.float64)

        trade_prices = np.asarray(state.get("trade_prices", []), dtype=np.float64)
        trade_sizes = np.asarray(state.get("trade_sizes", []), dtype=np.float64)
        trade_sides = np.asarray(state.get("trade_sides", []), dtype=np.float64)
        trade_times = np.asarray(state.get("trade_times", []), dtype=np.int64)

        if len(trade_prices) == 0:
            features[:] = np.nan
            return features

        last_price = trade_prices[-1]

        # Trade imbalance
        features[0] = compute_trade_imbalance(trade_sides, trade_sizes, 100)
        features[1] = compute_trade_imbalance(trade_sides, trade_sizes, 500)

        # Signed volume
        features[2] = compute_signed_volume(trade_sides, trade_sizes, 100)
        features[3] = compute_signed_volume(trade_sides, trade_sizes, 500)

        # VWAP
        features[4] = compute_vwap(trade_prices, trade_sizes, 100)
        features[5] = compute_vwap(trade_prices, trade_sizes, 500)

        # VWAP deviation
        features[6] = compute_vwap_deviation(last_price, trade_prices, trade_sizes, 100)
        features[7] = compute_vwap_deviation(last_price, trade_prices, trade_sizes, 500)

        # Flow toxicity
        features[8] = compute_trade_flow_toxicity(trade_sides, trade_sizes, 100)
        features[9] = compute_trade_flow_toxicity(trade_sides, trade_sizes, 500)

        # Trade rate
        if len(trade_times) > 0:
            features[10] = compute_trade_arrival_rate(trade_times, 1_000_000_000)
            features[11] = features[10]  # Same as count for 1 second
        else:
            features[10] = 0.0
            features[11] = 0.0

        # Trade size statistics
        n = min(100, len(trade_sizes))
        features[12] = np.mean(trade_sizes[-n:]) if n > 0 else np.nan
        features[13] = compute_trade_size_std(trade_sizes, 100)

        # Last trade info
        features[14] = trade_sides[-1] if len(trade_sides) > 0 else 0.0
        features[15] = trade_sizes[-1] if len(trade_sizes) > 0 else 0.0

        return features
