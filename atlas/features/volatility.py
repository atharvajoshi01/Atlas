"""Volatility feature computation."""

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
def compute_returns(prices: np.ndarray) -> np.ndarray:
    """Compute log returns from price series."""
    if len(prices) < 2:
        return np.array([0.0])

    returns = np.zeros(len(prices) - 1)
    for i in range(len(prices) - 1):
        if prices[i] > 0:
            returns[i] = np.log(prices[i + 1] / prices[i])
        else:
            returns[i] = 0.0
    return returns


@jit(nopython=True, cache=True)
def compute_realized_volatility(
    prices: np.ndarray,
    window: int = 100,
    annualization: float = np.sqrt(252.0 * 390.0 * 60.0)  # Assuming 1-minute data
) -> float:
    """Compute realized volatility from price series.

    Uses sum of squared returns (realized variance).
    """
    n = min(window, len(prices) - 1)
    if n < 2:
        return np.nan

    realized_var = 0.0
    for i in range(n):
        idx = len(prices) - 1 - i
        if prices[idx - 1] > 0:
            ret = np.log(prices[idx] / prices[idx - 1])
            realized_var += ret * ret

    realized_var /= n
    return np.sqrt(realized_var) * annualization


@jit(nopython=True, cache=True)
def compute_parkinson_volatility(
    highs: np.ndarray,
    lows: np.ndarray,
    window: int = 100,
    annualization: float = np.sqrt(252.0)
) -> float:
    """Compute Parkinson volatility estimator (high-low based).

    More efficient than close-to-close volatility.
    Parkinson = sqrt(1/(4*ln(2)) * avg((ln(H/L))^2))
    """
    n = min(window, len(highs), len(lows))
    if n < 1:
        return np.nan

    sum_sq = 0.0
    valid_count = 0

    for i in range(n):
        idx = len(highs) - 1 - i
        if lows[idx] > 0:
            log_hl = np.log(highs[idx] / lows[idx])
            sum_sq += log_hl * log_hl
            valid_count += 1

    if valid_count == 0:
        return np.nan

    # Parkinson constant: 1 / (4 * ln(2))
    parkinson_const = 1.0 / (4.0 * np.log(2.0))
    variance = parkinson_const * (sum_sq / valid_count)
    return np.sqrt(variance) * annualization


@jit(nopython=True, cache=True)
def compute_garman_klass_volatility(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    window: int = 100,
    annualization: float = np.sqrt(252.0)
) -> float:
    """Compute Garman-Klass volatility estimator (OHLC based).

    More efficient than Parkinson, uses all OHLC data.
    """
    n = min(window, len(opens), len(highs), len(lows), len(closes))
    if n < 1:
        return np.nan

    sum_var = 0.0
    valid_count = 0

    for i in range(n):
        idx = len(opens) - 1 - i
        if lows[idx] > 0 and opens[idx] > 0:
            log_hl = np.log(highs[idx] / lows[idx])
            log_co = np.log(closes[idx] / opens[idx])

            # Garman-Klass formula
            var = 0.5 * log_hl * log_hl - (2.0 * np.log(2.0) - 1.0) * log_co * log_co
            sum_var += var
            valid_count += 1

    if valid_count == 0:
        return np.nan

    variance = sum_var / valid_count
    if variance < 0:
        variance = 0.0
    return np.sqrt(variance) * annualization


@jit(nopython=True, cache=True)
def compute_yang_zhang_volatility(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    window: int = 100,
    annualization: float = np.sqrt(252.0)
) -> float:
    """Compute Yang-Zhang volatility estimator.

    Handles overnight jumps and is drift-independent.
    """
    n = min(window, len(opens) - 1)
    if n < 2:
        return np.nan

    # Overnight variance (close to open)
    overnight_var = 0.0
    # Open-to-close variance
    open_close_var = 0.0
    # Rogers-Satchell variance
    rs_var = 0.0

    for i in range(n):
        idx = len(opens) - 1 - i
        if closes[idx - 1] > 0 and opens[idx] > 0 and lows[idx] > 0:
            # Overnight return
            log_overnight = np.log(opens[idx] / closes[idx - 1])
            overnight_var += log_overnight * log_overnight

            # Open-to-close return
            log_oc = np.log(closes[idx] / opens[idx])
            open_close_var += log_oc * log_oc

            # Rogers-Satchell
            log_ho = np.log(highs[idx] / opens[idx])
            log_hc = np.log(highs[idx] / closes[idx])
            log_lo = np.log(lows[idx] / opens[idx])
            log_lc = np.log(lows[idx] / closes[idx])
            rs_var += log_ho * log_hc + log_lo * log_lc

    overnight_var /= (n - 1)
    open_close_var /= (n - 1)
    rs_var /= n

    # Yang-Zhang combination
    k = 0.34 / (1.0 + (n + 1.0) / (n - 1.0))
    variance = overnight_var + k * open_close_var + (1.0 - k) * rs_var

    if variance < 0:
        variance = 0.0
    return np.sqrt(variance) * annualization


@jit(nopython=True, cache=True)
def compute_vol_of_vol(
    volatilities: np.ndarray,
    window: int = 20
) -> float:
    """Compute volatility of volatility."""
    n = min(window, len(volatilities))
    if n < 2:
        return np.nan

    mean = 0.0
    for i in range(n):
        idx = len(volatilities) - 1 - i
        mean += volatilities[idx]
    mean /= n

    var = 0.0
    for i in range(n):
        idx = len(volatilities) - 1 - i
        var += (volatilities[idx] - mean) ** 2
    var /= (n - 1)

    return np.sqrt(var)


@jit(nopython=True, cache=True)
def compute_return_skewness(
    returns: np.ndarray,
    window: int = 100
) -> float:
    """Compute skewness of returns."""
    n = min(window, len(returns))
    if n < 3:
        return np.nan

    mean = 0.0
    for i in range(n):
        idx = len(returns) - 1 - i
        mean += returns[idx]
    mean /= n

    var = 0.0
    skew = 0.0
    for i in range(n):
        idx = len(returns) - 1 - i
        diff = returns[idx] - mean
        var += diff * diff
        skew += diff * diff * diff
    var /= n
    skew /= n

    std = np.sqrt(var)
    if std < 1e-10:
        return 0.0

    return skew / (std ** 3)


@jit(nopython=True, cache=True)
def compute_return_kurtosis(
    returns: np.ndarray,
    window: int = 100
) -> float:
    """Compute excess kurtosis of returns."""
    n = min(window, len(returns))
    if n < 4:
        return np.nan

    mean = 0.0
    for i in range(n):
        idx = len(returns) - 1 - i
        mean += returns[idx]
    mean /= n

    var = 0.0
    kurt = 0.0
    for i in range(n):
        idx = len(returns) - 1 - i
        diff = returns[idx] - mean
        var += diff * diff
        kurt += diff * diff * diff * diff
    var /= n
    kurt /= n

    var_sq = var * var
    if var_sq < 1e-20:
        return 0.0

    return (kurt / var_sq) - 3.0  # Excess kurtosis


class VolatilityFeatures(FeatureGenerator):
    """Volatility estimator features.

    Computes various volatility measures:
    - Realized volatility
    - Parkinson (high-low)
    - Garman-Klass (OHLC)
    - Yang-Zhang
    - Volatility of volatility
    - Return distribution moments
    """

    FEATURE_NAMES = [
        "realized_vol_100",
        "realized_vol_500",
        "parkinson_vol_100",
        "garman_klass_vol_100",
        "yang_zhang_vol_100",
        "vol_of_vol_20",
        "return_skewness_100",
        "return_kurtosis_100",
        "max_return_100",
        "min_return_100",
        "return_range_100",
    ]

    @property
    def feature_names(self) -> list[str]:
        return self.FEATURE_NAMES

    def compute(self, state: dict[str, Any]) -> np.ndarray:
        """Compute all volatility features.

        Args:
            state: Dictionary with keys:
                - prices: np.ndarray of prices (for realized vol)
                - opens: np.ndarray of open prices
                - highs: np.ndarray of high prices
                - lows: np.ndarray of low prices
                - closes: np.ndarray of close prices
                - volatilities: np.ndarray of historical volatilities (optional)

        Returns:
            numpy array of feature values.
        """
        features = np.zeros(len(self.FEATURE_NAMES), dtype=np.float64)

        prices = np.asarray(state.get("prices", []), dtype=np.float64)
        opens = np.asarray(state.get("opens", []), dtype=np.float64)
        highs = np.asarray(state.get("highs", []), dtype=np.float64)
        lows = np.asarray(state.get("lows", []), dtype=np.float64)
        closes = np.asarray(state.get("closes", []), dtype=np.float64)
        volatilities = np.asarray(state.get("volatilities", []), dtype=np.float64)

        if len(prices) < 2:
            features[:] = np.nan
            return features

        # Compute returns for distribution features
        returns = compute_returns(prices)

        # Realized volatility
        features[0] = compute_realized_volatility(prices, 100)
        features[1] = compute_realized_volatility(prices, 500)

        # Parkinson volatility (if high/low available)
        if len(highs) > 0 and len(lows) > 0:
            features[2] = compute_parkinson_volatility(highs, lows, 100)
        else:
            features[2] = np.nan

        # Garman-Klass volatility
        if len(opens) > 0 and len(highs) > 0 and len(lows) > 0 and len(closes) > 0:
            features[3] = compute_garman_klass_volatility(opens, highs, lows, closes, 100)
            features[4] = compute_yang_zhang_volatility(opens, highs, lows, closes, 100)
        else:
            features[3] = np.nan
            features[4] = np.nan

        # Vol of vol
        if len(volatilities) > 0:
            features[5] = compute_vol_of_vol(volatilities, 20)
        else:
            # Use realized vol as proxy
            features[5] = np.nan

        # Return distribution
        features[6] = compute_return_skewness(returns, 100)
        features[7] = compute_return_kurtosis(returns, 100)

        # Return range
        n = min(100, len(returns))
        if n > 0:
            recent_returns = returns[-n:]
            features[8] = np.max(recent_returns)
            features[9] = np.min(recent_returns)
            features[10] = features[8] - features[9]
        else:
            features[8] = np.nan
            features[9] = np.nan
            features[10] = np.nan

        return features
