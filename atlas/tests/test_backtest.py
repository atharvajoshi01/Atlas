"""Tests for the backtest engine."""

import numpy as np
import pandas as pd
import pytest

from atlas.backtest.engine import BacktestEngine, BacktestConfig, BacktestResult
from atlas.backtest.strategy import Signal, SimpleStrategy, Strategy, MarketState
from atlas.backtest.metrics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_calmar_ratio,
)


class TestBacktestConfig:
    """Tests for backtest configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BacktestConfig()
        assert config.initial_capital == 100000.0
        assert config.commission_per_share >= 0
        assert config.slippage_bps >= 0

    def test_custom_config(self):
        """Test custom configuration."""
        config = BacktestConfig(
            initial_capital=500000.0,
            commission_per_share=0.005,
            slippage_bps=2.0,
        )
        assert config.initial_capital == 500000.0
        assert config.commission_per_share == 0.005
        assert config.slippage_bps == 2.0


class TestSignal:
    """Tests for trading signals."""

    def test_signal_creation(self):
        """Test creating a signal."""
        signal = Signal(
            timestamp=1000,
            direction=1,
            size=100,
            price=100.0,
            confidence=0.8,
        )
        assert signal.direction == 1
        assert signal.size == 100
        assert signal.confidence == 0.8

    def test_signal_defaults(self):
        """Test signal default values."""
        signal = Signal(
            timestamp=1000,
            direction=1,
            size=100,
            price=100.0,
        )
        assert signal.urgency == 0.5
        assert signal.alpha == 0.0
        assert signal.confidence == 0.5
        assert signal.order_type == "limit"


class TestMarketState:
    """Tests for market state dataclass."""

    def test_market_state_creation(self):
        """Test creating a market state."""
        state = MarketState(
            timestamp=1000,
            mid_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            spread=0.1,
        )
        assert state.mid_price == 100.0
        assert state.spread == 0.1

    def test_market_state_defaults(self):
        """Test market state defaults."""
        state = MarketState(
            timestamp=1000,
            mid_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            spread=0.1,
        )
        assert state.position == 0.0
        assert state.equity == 0.0


class TestSimpleStrategy:
    """Tests for the simple strategy implementation."""

    def test_strategy_creation(self):
        """Test creating a simple strategy."""
        strategy = SimpleStrategy(imbalance_threshold=0.3)
        assert strategy.imbalance_threshold == 0.3

    def test_strategy_no_signal_below_threshold(self):
        """Test no signal when imbalance below threshold."""
        strategy = SimpleStrategy(imbalance_threshold=0.3)

        state = MarketState(
            timestamp=1000,
            mid_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            spread=0.1,
            features={"imbalance_5": 0.1},  # Below threshold
        )

        signal = strategy.on_market_data(state)
        assert signal is None

    def test_strategy_buy_signal(self):
        """Test buy signal on positive imbalance."""
        strategy = SimpleStrategy(imbalance_threshold=0.2)

        state = MarketState(
            timestamp=1000,
            mid_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            spread=0.1,
            features={"imbalance_5": 0.4},  # Above threshold
            position=0.0,
        )

        signal = strategy.on_market_data(state)
        assert signal is not None
        assert signal.direction == 1

    def test_strategy_sell_signal(self):
        """Test sell signal on negative imbalance."""
        strategy = SimpleStrategy(imbalance_threshold=0.2)

        state = MarketState(
            timestamp=1000,
            mid_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            spread=0.1,
            features={"imbalance_5": -0.4},  # Below negative threshold
            position=0.0,
        )

        signal = strategy.on_market_data(state)
        assert signal is not None
        assert signal.direction == -1


class TestMetrics:
    """Tests for performance metrics."""

    def test_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.01, 252)

        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02, periods_per_year=252)
        assert -5 < sharpe < 5  # Sanity check

    def test_sharpe_ratio_zero_std(self):
        """Test Sharpe ratio with zero standard deviation."""
        returns = np.ones(100) * 0.001
        sharpe = calculate_sharpe_ratio(returns)
        assert sharpe == 0.0

    def test_sortino_ratio(self):
        """Test Sortino ratio calculation."""
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.01, 252)

        sortino = calculate_sortino_ratio(returns, risk_free_rate=0.02, periods_per_year=252)
        assert isinstance(sortino, float)

    def test_max_drawdown(self):
        """Test maximum drawdown calculation."""
        equity = np.array([100.0, 105.0, 110.0, 100.0, 95.0, 105.0, 115.0, 110.0])

        drawdown, peak_idx, trough_idx = calculate_max_drawdown(equity)
        # Max drawdown from 110 to 95 = 13.6%
        assert np.isclose(drawdown, (110 - 95) / 110, atol=0.01)
        assert peak_idx == 2  # Peak at 110
        assert trough_idx == 4  # Trough at 95

    def test_max_drawdown_no_drawdown(self):
        """Test max drawdown when equity only goes up."""
        equity = np.array([100.0, 105.0, 110.0, 115.0, 120.0])

        drawdown, _, _ = calculate_max_drawdown(equity)
        assert drawdown == 0.0

    def test_calmar_ratio(self):
        """Test Calmar ratio calculation."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 252)

        calmar = calculate_calmar_ratio(returns, periods_per_year=252)
        assert isinstance(calmar, float)


class TestBacktestEngine:
    """Tests for the backtest engine."""

    def test_engine_creation(self):
        """Test creating a backtest engine."""
        config = BacktestConfig(initial_capital=100000.0)
        engine = BacktestEngine(config)
        assert engine.config.initial_capital == 100000.0

    def test_engine_run_simple(self):
        """Test running a simple backtest."""
        config = BacktestConfig(initial_capital=100000.0)
        engine = BacktestEngine(config)
        strategy = SimpleStrategy(imbalance_threshold=0.2)

        # Create simple market data
        n_periods = 100
        np.random.seed(42)

        market_data = pd.DataFrame({
            "timestamp": range(n_periods),
            "mid_price": 100.0 + np.cumsum(np.random.normal(0, 0.1, n_periods)),
            "bid_price": 100.0 + np.cumsum(np.random.normal(0, 0.1, n_periods)) - 0.05,
            "ask_price": 100.0 + np.cumsum(np.random.normal(0, 0.1, n_periods)) + 0.05,
            "imbalance_5": np.random.uniform(-0.5, 0.5, n_periods),
        })

        features = pd.DataFrame({
            "imbalance_5": market_data["imbalance_5"],
        })

        result = engine.run(strategy, market_data, features)
        assert isinstance(result, BacktestResult)
        assert hasattr(result, "sharpe_ratio")
        assert hasattr(result, "max_drawdown")
        assert hasattr(result, "total_return")

    def test_engine_equity_curve(self):
        """Test that equity curve is generated."""
        config = BacktestConfig(initial_capital=100000.0)
        engine = BacktestEngine(config)
        strategy = SimpleStrategy(imbalance_threshold=0.5)

        n_periods = 50
        np.random.seed(42)

        market_data = pd.DataFrame({
            "timestamp": range(n_periods),
            "mid_price": 100.0 + np.random.normal(0, 0.1, n_periods).cumsum(),
            "bid_price": 99.95 + np.random.normal(0, 0.1, n_periods).cumsum(),
            "ask_price": 100.05 + np.random.normal(0, 0.1, n_periods).cumsum(),
            "imbalance_5": np.random.uniform(-0.3, 0.3, n_periods),
        })

        features = pd.DataFrame({
            "imbalance_5": market_data["imbalance_5"],
        })

        result = engine.run(strategy, market_data, features)
        assert len(result.equity_curve) == n_periods
