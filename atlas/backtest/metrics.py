"""Performance metrics for backtesting."""

import numpy as np
from typing import Tuple


def calculate_sharpe_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
) -> float:
    """Calculate annualized Sharpe ratio.

    Args:
        returns: Array of periodic returns.
        risk_free_rate: Annual risk-free rate.
        periods_per_year: Trading periods per year (252 for daily).

    Returns:
        Annualized Sharpe ratio.
    """
    if len(returns) < 2:
        return 0.0

    excess_returns = returns - risk_free_rate / periods_per_year
    std = np.std(excess_returns, ddof=1)

    if std < 1e-10:  # Near-zero standard deviation
        return 0.0

    return np.mean(excess_returns) / std * np.sqrt(periods_per_year)


def calculate_sortino_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
) -> float:
    """Calculate annualized Sortino ratio.

    Uses downside deviation instead of standard deviation.

    Args:
        returns: Array of periodic returns.
        risk_free_rate: Annual risk-free rate.
        periods_per_year: Trading periods per year.

    Returns:
        Annualized Sortino ratio.
    """
    if len(returns) < 2:
        return 0.0

    target_return = risk_free_rate / periods_per_year
    excess_returns = returns - target_return

    # Downside deviation: std of negative excess returns
    negative_returns = excess_returns[excess_returns < 0]
    if len(negative_returns) < 2:
        downside_std = 0.0
    else:
        downside_std = np.std(negative_returns, ddof=1)

    if downside_std == 0:
        return 0.0

    return np.mean(excess_returns) / downside_std * np.sqrt(periods_per_year)


def calculate_max_drawdown(
    equity: np.ndarray,
) -> Tuple[float, int, int]:
    """Calculate maximum drawdown and its location.

    Args:
        equity: Equity curve (cumulative returns or portfolio value).

    Returns:
        Tuple of (max_drawdown, peak_idx, trough_idx).
    """
    if len(equity) < 2:
        return 0.0, 0, 0

    # Running maximum
    running_max = np.maximum.accumulate(equity)

    # Drawdown at each point
    drawdowns = (running_max - equity) / running_max

    # Maximum drawdown
    max_dd = np.max(drawdowns)
    trough_idx = int(np.argmax(drawdowns))

    # Find the peak before the trough
    peak_idx = int(np.argmax(equity[:trough_idx + 1]))

    return float(max_dd), peak_idx, trough_idx


def calculate_calmar_ratio(
    returns: np.ndarray,
    periods_per_year: int = 252,
) -> float:
    """Calculate Calmar ratio (annual return / max drawdown).

    Args:
        returns: Array of periodic returns.
        periods_per_year: Trading periods per year.

    Returns:
        Calmar ratio.
    """
    if len(returns) < 2:
        return 0.0

    # Calculate equity curve
    equity = np.cumprod(1 + returns)

    max_dd, _, _ = calculate_max_drawdown(equity)

    if max_dd == 0:
        return 0.0

    # Annualized return
    total_return = equity[-1] / equity[0] - 1
    years = len(returns) / periods_per_year
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

    return annual_return / max_dd


def calculate_information_ratio(
    returns: np.ndarray,
    benchmark_returns: np.ndarray,
    periods_per_year: int = 252,
) -> float:
    """Calculate Information Ratio relative to benchmark.

    Args:
        returns: Strategy returns.
        benchmark_returns: Benchmark returns.
        periods_per_year: Trading periods per year.

    Returns:
        Annualized Information Ratio.
    """
    if len(returns) != len(benchmark_returns):
        raise ValueError("Returns and benchmark must have same length")

    if len(returns) < 2:
        return 0.0

    active_returns = returns - benchmark_returns
    tracking_error = np.std(active_returns, ddof=1)

    if tracking_error == 0:
        return 0.0

    return np.mean(active_returns) / tracking_error * np.sqrt(periods_per_year)


def calculate_win_rate(
    returns: np.ndarray,
) -> float:
    """Calculate win rate (percentage of positive returns).

    Args:
        returns: Array of returns.

    Returns:
        Win rate as a decimal.
    """
    if len(returns) == 0:
        return 0.0

    return np.sum(returns > 0) / len(returns)


def calculate_profit_factor(
    returns: np.ndarray,
) -> float:
    """Calculate profit factor (gross profit / gross loss).

    Args:
        returns: Array of returns.

    Returns:
        Profit factor (> 1 is profitable).
    """
    gross_profit = np.sum(returns[returns > 0])
    gross_loss = np.abs(np.sum(returns[returns < 0]))

    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0

    return gross_profit / gross_loss


def calculate_avg_win_loss_ratio(
    returns: np.ndarray,
) -> float:
    """Calculate average win / average loss ratio.

    Args:
        returns: Array of returns.

    Returns:
        Average win/loss ratio.
    """
    wins = returns[returns > 0]
    losses = returns[returns < 0]

    if len(wins) == 0 or len(losses) == 0:
        return 0.0

    avg_win = np.mean(wins)
    avg_loss = np.abs(np.mean(losses))

    if avg_loss == 0:
        return float('inf')

    return avg_win / avg_loss
