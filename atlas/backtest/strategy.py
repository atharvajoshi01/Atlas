"""Strategy interface for backtesting."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class Signal:
    """Trading signal output from strategy."""

    timestamp: int  # Nanoseconds since epoch
    direction: int  # 1 = buy, -1 = sell, 0 = flat
    size: float     # Target position size
    price: float    # Limit price (0 for market order)
    urgency: float = 0.5  # 0-1, affects execution aggressiveness
    alpha: float = 0.0    # Expected alpha/edge
    confidence: float = 0.5  # Signal confidence
    order_type: str = "limit"  # "limit" or "market"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Fill:
    """Execution fill notification."""

    timestamp: int
    order_id: int
    side: int  # 1 = buy, -1 = sell
    price: float
    quantity: float
    commission: float = 0.0
    slippage: float = 0.0


@dataclass
class MarketState:
    """Current market state provided to strategy."""

    timestamp: int
    mid_price: float
    bid_price: float
    ask_price: float
    spread: float
    bid_size: float = 0.0
    ask_size: float = 0.0
    last_trade_price: float = 0.0
    last_trade_size: float = 0.0
    features: dict[str, float] = field(default_factory=dict)

    # Position info
    position: float = 0.0
    avg_cost: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    cash: float = 0.0
    equity: float = 0.0


class Strategy(ABC):
    """Abstract base class for trading strategies.

    Implement this class to create custom trading strategies.

    Example:
        class MomentumStrategy(Strategy):
            def on_market_data(self, state: MarketState) -> Signal | None:
                alpha = state.features.get("imbalance", 0)
                if alpha > 0.02:
                    return Signal(
                        timestamp=state.timestamp,
                        direction=1,
                        size=100,
                        price=state.bid_price
                    )
                return None
    """

    def __init__(self, name: str = "unnamed"):
        """Initialize strategy.

        Args:
            name: Strategy name for identification.
        """
        self.name = name
        self._position = 0.0
        self._pnl = 0.0
        self._trades = []

    @abstractmethod
    def on_market_data(self, state: MarketState) -> Signal | None:
        """Process market update and optionally generate signal.

        Called on each market data update.

        Args:
            state: Current market state including position info.

        Returns:
            Signal if action should be taken, None otherwise.
        """
        pass

    def on_fill(self, fill: Fill) -> None:
        """Handle execution confirmation.

        Override to implement custom fill handling.

        Args:
            fill: Fill notification.
        """
        self._trades.append(fill)

    def on_day_start(self, date: str) -> None:
        """Called at start of trading day.

        Override for daily initialization.

        Args:
            date: Date string (YYYY-MM-DD).
        """
        pass

    def on_day_end(self, date: str) -> None:
        """Called at end of trading day.

        Override for daily cleanup or position flattening.

        Args:
            date: Date string (YYYY-MM-DD).
        """
        pass

    def reset(self) -> None:
        """Reset strategy state for new backtest."""
        self._position = 0.0
        self._pnl = 0.0
        self._trades = []

    @property
    def position(self) -> float:
        """Current position."""
        return self._position

    @property
    def pnl(self) -> float:
        """Cumulative PnL."""
        return self._pnl

    @property
    def trade_count(self) -> int:
        """Number of trades executed."""
        return len(self._trades)


class AlphaStrategy(Strategy):
    """Strategy based on alpha signal predictions.

    Simple implementation that trades based on alpha signal thresholds.
    """

    def __init__(
        self,
        alpha_model,
        feature_pipeline,
        entry_threshold: float = 0.02,
        exit_threshold: float = 0.005,
        max_position: float = 1000,
        name: str = "alpha_strategy"
    ):
        """Initialize alpha strategy.

        Args:
            alpha_model: Fitted AlphaSignal model.
            feature_pipeline: FeaturePipeline for computing features.
            entry_threshold: Alpha threshold for entry.
            exit_threshold: Alpha threshold for exit.
            max_position: Maximum position size.
            name: Strategy name.
        """
        super().__init__(name)
        self.alpha_model = alpha_model
        self.feature_pipeline = feature_pipeline
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.max_position = max_position
        self._current_alpha = 0.0

    def on_market_data(self, state: MarketState) -> Signal | None:
        """Generate signal based on alpha prediction."""
        # Get alpha prediction
        if state.features:
            import pandas as pd
            features_df = pd.DataFrame([state.features])
            try:
                alpha = self.alpha_model.predict(features_df)[0]
            except Exception:
                alpha = 0.0
        else:
            alpha = 0.0

        self._current_alpha = alpha

        # Entry logic
        if abs(state.position) < self.max_position:
            if alpha > self.entry_threshold:
                target_size = min(
                    self.max_position - state.position,
                    self.max_position * abs(alpha) / 0.05  # Scale by alpha
                )
                return Signal(
                    timestamp=state.timestamp,
                    direction=1,
                    size=target_size,
                    price=state.bid_price,
                    urgency=min(1.0, abs(alpha) / 0.05),
                    alpha=alpha,
                    confidence=0.6
                )
            elif alpha < -self.entry_threshold:
                target_size = min(
                    self.max_position + state.position,
                    self.max_position * abs(alpha) / 0.05
                )
                return Signal(
                    timestamp=state.timestamp,
                    direction=-1,
                    size=target_size,
                    price=state.ask_price,
                    urgency=min(1.0, abs(alpha) / 0.05),
                    alpha=alpha,
                    confidence=0.6
                )

        # Exit logic
        if state.position > 0 and alpha < self.exit_threshold:
            return Signal(
                timestamp=state.timestamp,
                direction=-1,
                size=state.position,
                price=state.ask_price,
                urgency=0.3,
                alpha=alpha,
                confidence=0.5
            )
        elif state.position < 0 and alpha > -self.exit_threshold:
            return Signal(
                timestamp=state.timestamp,
                direction=1,
                size=abs(state.position),
                price=state.bid_price,
                urgency=0.3,
                alpha=alpha,
                confidence=0.5
            )

        return None


class SimpleStrategy(Strategy):
    """Simple strategy for testing.

    Trades based on order book imbalance.
    """

    def __init__(
        self,
        imbalance_threshold: float = 0.3,
        max_position: float = 100,
        name: str = "simple_strategy"
    ):
        super().__init__(name)
        self.imbalance_threshold = imbalance_threshold
        self.max_position = max_position

    def on_market_data(self, state: MarketState) -> Signal | None:
        imbalance = state.features.get("imbalance_5", 0)

        if state.position < self.max_position and imbalance > self.imbalance_threshold:
            return Signal(
                timestamp=state.timestamp,
                direction=1,
                size=100,
                price=state.bid_price,
                alpha=imbalance
            )
        elif state.position > -self.max_position and imbalance < -self.imbalance_threshold:
            return Signal(
                timestamp=state.timestamp,
                direction=-1,
                size=100,
                price=state.ask_price,
                alpha=imbalance
            )

        return None
