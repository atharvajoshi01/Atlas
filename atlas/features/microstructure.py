"""Market microstructure feature computation."""

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
def compute_kyles_lambda(
    price_changes: np.ndarray,
    signed_volumes: np.ndarray,
    window: int = 100
) -> float:
    """Estimate Kyle's lambda (price impact coefficient).

    Lambda = Cov(dP, SignedVolume) / Var(SignedVolume)

    Higher lambda = more price impact per unit of signed volume = less liquid.
    """
    n = min(window, len(price_changes), len(signed_volumes))
    if n < 10:
        return np.nan

    # Use last n observations
    dp = price_changes[-n:]
    sv = signed_volumes[-n:]

    # Compute means
    mean_dp = 0.0
    mean_sv = 0.0
    for i in range(n):
        mean_dp += dp[i]
        mean_sv += sv[i]
    mean_dp /= n
    mean_sv /= n

    # Compute covariance and variance
    cov = 0.0
    var_sv = 0.0
    for i in range(n):
        cov += (dp[i] - mean_dp) * (sv[i] - mean_sv)
        var_sv += (sv[i] - mean_sv) ** 2

    cov /= (n - 1)
    var_sv /= (n - 1)

    if var_sv < 1e-10:
        return np.nan

    return cov / var_sv


@jit(nopython=True, cache=True)
def compute_effective_spread(
    trade_prices: np.ndarray,
    mid_prices: np.ndarray,
    window: int = 100
) -> float:
    """Compute effective spread.

    Effective Spread = 2 * mean(|trade_price - mid_price|)

    Measures actual transaction costs paid by traders.
    """
    n = min(window, len(trade_prices), len(mid_prices))
    if n == 0:
        return np.nan

    spread_sum = 0.0
    for i in range(n):
        idx = len(trade_prices) - 1 - i
        spread_sum += abs(trade_prices[idx] - mid_prices[idx])

    return 2.0 * spread_sum / n


@jit(nopython=True, cache=True)
def compute_realized_spread(
    trade_prices: np.ndarray,
    trade_sides: np.ndarray,
    future_mid_prices: np.ndarray,
    window: int = 100
) -> float:
    """Compute realized spread.

    Realized Spread = 2 * side * (trade_price - future_mid)

    Measures market maker profitability after adverse selection.
    """
    n = min(window, len(trade_prices), len(trade_sides), len(future_mid_prices))
    if n == 0:
        return np.nan

    spread_sum = 0.0
    valid_count = 0
    for i in range(n):
        idx = len(trade_prices) - 1 - i
        if not np.isnan(future_mid_prices[idx]):
            spread_sum += 2.0 * trade_sides[idx] * (
                trade_prices[idx] - future_mid_prices[idx]
            )
            valid_count += 1

    if valid_count == 0:
        return np.nan

    return spread_sum / valid_count


@jit(nopython=True, cache=True)
def compute_price_impact(
    trade_prices: np.ndarray,
    mid_prices_before: np.ndarray,
    mid_prices_after: np.ndarray,
    trade_sides: np.ndarray,
    window: int = 100
) -> float:
    """Compute permanent price impact.

    Price Impact = side * (mid_after - mid_before)

    Measures how much prices move in the direction of the trade.
    """
    n = min(window, len(trade_prices), len(mid_prices_before),
            len(mid_prices_after), len(trade_sides))
    if n == 0:
        return np.nan

    impact_sum = 0.0
    for i in range(n):
        idx = len(trade_prices) - 1 - i
        impact_sum += trade_sides[idx] * (
            mid_prices_after[idx] - mid_prices_before[idx]
        )

    return impact_sum / n


@jit(nopython=True, cache=True)
def compute_roll_spread(
    price_changes: np.ndarray,
    window: int = 100
) -> float:
    """Compute Roll spread estimator.

    Roll Spread = 2 * sqrt(-Cov(dP_t, dP_{t-1}))

    Uses autocovariance of price changes to estimate spread.
    """
    n = min(window, len(price_changes) - 1)
    if n < 10:
        return np.nan

    # Compute autocovariance at lag 1
    mean = 0.0
    for i in range(n + 1):
        idx = len(price_changes) - 1 - i
        mean += price_changes[idx]
    mean /= (n + 1)

    cov = 0.0
    for i in range(n):
        idx = len(price_changes) - 1 - i
        cov += (price_changes[idx] - mean) * (price_changes[idx - 1] - mean)
    cov /= n

    # Roll spread: negative covariance implies spread
    if cov >= 0:
        return 0.0  # No spread detected

    return 2.0 * np.sqrt(-cov)


@jit(nopython=True, cache=True)
def compute_amihud_illiquidity(
    returns: np.ndarray,
    volumes: np.ndarray,
    window: int = 20
) -> float:
    """Compute Amihud illiquidity ratio.

    Amihud = mean(|return| / volume)

    Higher values indicate less liquid (more price impact per unit volume).
    """
    n = min(window, len(returns), len(volumes))
    if n == 0:
        return np.nan

    illiq_sum = 0.0
    valid_count = 0
    for i in range(n):
        idx = len(returns) - 1 - i
        if volumes[idx] > 0:
            illiq_sum += abs(returns[idx]) / volumes[idx]
            valid_count += 1

    if valid_count == 0:
        return np.nan

    return illiq_sum / valid_count


@jit(nopython=True, cache=True)
def compute_order_flow_autocorrelation(
    order_sides: np.ndarray,
    lag: int = 1,
    window: int = 100
) -> float:
    """Compute autocorrelation of order flow.

    Measures persistence in order flow direction.
    """
    n = min(window, len(order_sides) - lag)
    if n < 10:
        return np.nan

    # Simple autocorrelation at specified lag
    mean = 0.0
    for i in range(n + lag):
        idx = len(order_sides) - 1 - i
        mean += order_sides[idx]
    mean /= (n + lag)

    cov = 0.0
    var = 0.0
    for i in range(n):
        idx = len(order_sides) - 1 - i
        cov += (order_sides[idx] - mean) * (order_sides[idx - lag] - mean)
        var += (order_sides[idx] - mean) ** 2

    if var < 1e-10:
        return 0.0

    return cov / var


class MicrostructureFeatures(FeatureGenerator):
    """Market microstructure features.

    Computes features related to market quality and trading costs:
    - Kyle's lambda (price impact coefficient)
    - Effective spread
    - Realized spread
    - Price impact
    - Roll spread
    - Amihud illiquidity
    - Order flow persistence
    """

    FEATURE_NAMES = [
        "kyles_lambda_100",
        "kyles_lambda_500",
        "effective_spread_100",
        "realized_spread_100",
        "price_impact_100",
        "roll_spread_100",
        "amihud_illiquidity_20",
        "order_flow_autocorr_1",
        "order_flow_autocorr_5",
        "adverse_selection",
        "liquidity_score",
    ]

    @property
    def feature_names(self) -> list[str]:
        return self.FEATURE_NAMES

    def compute(self, state: dict[str, Any]) -> np.ndarray:
        """Compute all microstructure features.

        Args:
            state: Dictionary with keys:
                - price_changes: np.ndarray of price changes
                - signed_volumes: np.ndarray of signed trade volumes
                - trade_prices: np.ndarray of trade prices
                - trade_sides: np.ndarray of trade sides (1=buy, -1=sell)
                - mid_prices: np.ndarray of mid prices at trade time
                - future_mid_prices: np.ndarray of mid prices after trade
                - returns: np.ndarray of returns
                - volumes: np.ndarray of volumes

        Returns:
            numpy array of feature values.
        """
        features = np.zeros(len(self.FEATURE_NAMES), dtype=np.float64)

        price_changes = np.asarray(state.get("price_changes", []), dtype=np.float64)
        signed_volumes = np.asarray(state.get("signed_volumes", []), dtype=np.float64)
        trade_prices = np.asarray(state.get("trade_prices", []), dtype=np.float64)
        trade_sides = np.asarray(state.get("trade_sides", []), dtype=np.float64)
        mid_prices = np.asarray(state.get("mid_prices", []), dtype=np.float64)
        future_mid_prices = np.asarray(state.get("future_mid_prices", []), dtype=np.float64)
        returns = np.asarray(state.get("returns", []), dtype=np.float64)
        volumes = np.asarray(state.get("volumes", []), dtype=np.float64)

        # Kyle's lambda
        features[0] = compute_kyles_lambda(price_changes, signed_volumes, 100)
        features[1] = compute_kyles_lambda(price_changes, signed_volumes, 500)

        # Effective spread
        if len(trade_prices) > 0 and len(mid_prices) > 0:
            features[2] = compute_effective_spread(trade_prices, mid_prices, 100)
        else:
            features[2] = np.nan

        # Realized spread
        if len(future_mid_prices) > 0:
            features[3] = compute_realized_spread(
                trade_prices, trade_sides, future_mid_prices, 100
            )
        else:
            features[3] = np.nan

        # Price impact
        mid_prices_before = np.asarray(state.get("mid_prices_before", []), dtype=np.float64)
        mid_prices_after = np.asarray(state.get("mid_prices_after", []), dtype=np.float64)
        if len(mid_prices_before) > 0 and len(mid_prices_after) > 0:
            features[4] = compute_price_impact(
                trade_prices, mid_prices_before, mid_prices_after, trade_sides, 100
            )
        else:
            features[4] = np.nan

        # Roll spread
        features[5] = compute_roll_spread(price_changes, 100)

        # Amihud illiquidity
        features[6] = compute_amihud_illiquidity(returns, volumes, 20)

        # Order flow autocorrelation
        features[7] = compute_order_flow_autocorrelation(trade_sides, 1, 100)
        features[8] = compute_order_flow_autocorrelation(trade_sides, 5, 100)

        # Adverse selection (realized spread < effective spread)
        if not np.isnan(features[2]) and not np.isnan(features[3]):
            features[9] = features[2] - features[3]  # Positive = adverse selection
        else:
            features[9] = np.nan

        # Composite liquidity score
        # Normalize and combine multiple measures
        lambda_score = 1.0 / (1.0 + abs(features[0])) if not np.isnan(features[0]) else 0.5
        spread_score = 1.0 / (1.0 + features[2]) if not np.isnan(features[2]) else 0.5
        amihud_score = 1.0 / (1.0 + features[6] * 1e6) if not np.isnan(features[6]) else 0.5
        features[10] = (lambda_score + spread_score + amihud_score) / 3.0

        return features
