"""Backtest engine for strategy simulation."""

from dataclasses import dataclass, field
from typing import Any
import numpy as np
import pandas as pd

from atlas.backtest.strategy import Strategy, Signal, Fill, MarketState


@dataclass
class BacktestConfig:
    """Configuration for backtest."""

    initial_capital: float = 100000.0
    commission_per_share: float = 0.001
    commission_min: float = 1.0
    slippage_bps: float = 1.0  # Slippage in basis points
    market_impact_coef: float = 0.1  # Square-root impact coefficient
    max_position: float = 10000
    margin_requirement: float = 0.5
    borrowing_rate: float = 0.02  # Annual
    risk_free_rate: float = 0.02  # Annual


@dataclass
class BacktestResult:
    """Results from backtest run."""

    # Summary metrics
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float

    # Trade statistics
    total_trades: int
    avg_trade_pnl: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float

    # Time series
    equity_curve: pd.Series
    returns: pd.Series
    positions: pd.Series
    drawdowns: pd.Series

    # Detailed data
    trades: pd.DataFrame
    daily_stats: pd.DataFrame


class BacktestEngine:
    """Backtest engine with realistic execution simulation.

    Features:
    - Transaction costs (commission, spread)
    - Market impact modeling
    - Position and risk tracking
    - Performance attribution

    Example:
        engine = BacktestEngine(config)
        result = engine.run(strategy, market_data)
        print(f"Sharpe: {result.sharpe_ratio:.2f}")
    """

    def __init__(self, config: BacktestConfig | None = None):
        """Initialize backtest engine.

        Args:
            config: Backtest configuration.
        """
        self.config = config or BacktestConfig()
        self._reset()

    def _reset(self) -> None:
        """Reset engine state."""
        self.cash = self.config.initial_capital
        self.position = 0.0
        self.avg_cost = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.equity_history = []
        self.position_history = []
        self.trade_history = []
        self.timestamp_history = []
        self._current_timestamp = 0

    def run(
        self,
        strategy: Strategy,
        market_data: pd.DataFrame,
        features: pd.DataFrame | None = None
    ) -> BacktestResult:
        """Run backtest on market data.

        Args:
            strategy: Strategy to backtest.
            market_data: DataFrame with columns:
                - timestamp, bid_price, ask_price, mid_price
                - Optional: bid_size, ask_size, last_price, volume
            features: Optional pre-computed features DataFrame.

        Returns:
            BacktestResult with performance metrics.
        """
        self._reset()
        strategy.reset()

        for idx, row in market_data.iterrows():
            self._current_timestamp = row.get("timestamp", idx)

            # Build market state
            state = self._build_market_state(row, features, idx)

            # Get strategy signal
            signal = strategy.on_market_data(state)

            # Execute signal if present
            if signal is not None:
                fill = self._execute_signal(signal, state)
                if fill is not None:
                    strategy.on_fill(fill)

            # Update equity
            self._update_equity(state.mid_price)

        return self._compute_results()

    def _build_market_state(
        self,
        row: pd.Series,
        features: pd.DataFrame | None,
        idx: Any
    ) -> MarketState:
        """Build market state from data row."""
        mid_price = row.get("mid_price", (row["bid_price"] + row["ask_price"]) / 2)

        # Get features if available
        feature_dict = {}
        if features is not None and idx in features.index:
            feature_dict = features.loc[idx].to_dict()

        return MarketState(
            timestamp=row.get("timestamp", 0),
            mid_price=mid_price,
            bid_price=row["bid_price"],
            ask_price=row["ask_price"],
            spread=row["ask_price"] - row["bid_price"],
            bid_size=row.get("bid_size", 0),
            ask_size=row.get("ask_size", 0),
            last_trade_price=row.get("last_price", mid_price),
            last_trade_size=row.get("volume", 0),
            features=feature_dict,
            position=self.position,
            avg_cost=self.avg_cost,
            unrealized_pnl=self.unrealized_pnl,
            realized_pnl=self.realized_pnl,
            cash=self.cash,
            equity=self.cash + self.position * mid_price,
        )

    def _execute_signal(self, signal: Signal, state: MarketState) -> Fill | None:
        """Execute a trading signal.

        Simulates execution with costs and market impact.
        """
        # Determine execution price with slippage and impact
        base_price = signal.price if signal.price > 0 else (
            state.ask_price if signal.direction > 0 else state.bid_price
        )

        # Slippage
        slippage = base_price * self.config.slippage_bps / 10000
        if signal.direction > 0:
            slippage = abs(slippage)  # Pay more when buying
        else:
            slippage = -abs(slippage)  # Receive less when selling

        # Market impact (square root model)
        impact = (
            self.config.market_impact_coef *
            np.sqrt(abs(signal.size) / 1000) *
            base_price / 100
        )
        if signal.direction > 0:
            impact = abs(impact)
        else:
            impact = -abs(impact)

        exec_price = base_price + slippage + impact

        # Commission
        commission = max(
            abs(signal.size) * self.config.commission_per_share,
            self.config.commission_min
        )

        # Execute trade
        trade_value = signal.direction * signal.size * exec_price

        # Update position
        if signal.direction > 0:
            # Buying
            new_position = self.position + signal.size
            if self.position >= 0:
                # Adding to long
                self.avg_cost = (
                    (self.avg_cost * self.position + exec_price * signal.size) /
                    new_position
                ) if new_position > 0 else 0
            else:
                # Covering short
                covered = min(signal.size, abs(self.position))
                self.realized_pnl += covered * (self.avg_cost - exec_price)
                remaining = signal.size - covered
                if remaining > 0:
                    self.avg_cost = exec_price
        else:
            # Selling
            new_position = self.position - signal.size
            if self.position <= 0:
                # Adding to short
                self.avg_cost = (
                    (self.avg_cost * abs(self.position) + exec_price * signal.size) /
                    abs(new_position)
                ) if new_position < 0 else 0
            else:
                # Closing long
                closed = min(signal.size, self.position)
                self.realized_pnl += closed * (exec_price - self.avg_cost)
                remaining = signal.size - closed
                if remaining > 0:
                    self.avg_cost = exec_price

        self.position = new_position
        self.cash -= trade_value + commission

        # Record trade
        fill = Fill(
            timestamp=signal.timestamp,
            order_id=len(self.trade_history) + 1,
            side=signal.direction,
            price=exec_price,
            quantity=signal.size,
            commission=commission,
            slippage=abs(slippage) + abs(impact)
        )
        self.trade_history.append(fill)

        return fill

    def _update_equity(self, current_price: float) -> None:
        """Update equity and unrealized PnL."""
        if self.position != 0:
            self.unrealized_pnl = self.position * (current_price - self.avg_cost)
        else:
            self.unrealized_pnl = 0

        equity = self.cash + self.position * current_price
        self.equity_history.append(equity)
        self.position_history.append(self.position)
        self.timestamp_history.append(self._current_timestamp)

    def _compute_results(self) -> BacktestResult:
        """Compute backtest results and metrics."""
        equity = pd.Series(self.equity_history, index=self.timestamp_history)
        positions = pd.Series(self.position_history, index=self.timestamp_history)

        # Returns
        returns = equity.pct_change().dropna()

        # Drawdown
        peak = equity.expanding().max()
        drawdown = (equity - peak) / peak

        # Trade statistics
        trades_df = self._build_trades_df()
        trade_pnls = trades_df["pnl"] if len(trades_df) > 0 else pd.Series([0])

        wins = trade_pnls[trade_pnls > 0]
        losses = trade_pnls[trade_pnls < 0]

        # Metrics
        total_return = (equity.iloc[-1] / self.config.initial_capital - 1) if len(equity) > 0 else 0
        n_days = max(len(equity) / 390, 1)  # Assume 390 minutes per day
        annual_return = (1 + total_return) ** (252 / n_days) - 1 if n_days > 0 else 0

        # Sharpe ratio
        if len(returns) > 1 and returns.std() > 0:
            sharpe = returns.mean() / returns.std() * np.sqrt(252 * 390)
        else:
            sharpe = 0.0

        # Sortino ratio
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 1 and downside_returns.std() > 0:
            sortino = returns.mean() / downside_returns.std() * np.sqrt(252 * 390)
        else:
            sortino = 0.0

        max_dd = abs(drawdown.min()) if len(drawdown) > 0 else 0
        calmar = annual_return / max_dd if max_dd > 0 else 0

        win_rate = len(wins) / len(trade_pnls) if len(trade_pnls) > 0 else 0
        gross_profit = wins.sum() if len(wins) > 0 else 0
        gross_loss = abs(losses.sum()) if len(losses) > 0 else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            calmar_ratio=calmar,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(self.trade_history),
            avg_trade_pnl=trade_pnls.mean() if len(trade_pnls) > 0 else 0,
            avg_win=wins.mean() if len(wins) > 0 else 0,
            avg_loss=losses.mean() if len(losses) > 0 else 0,
            largest_win=wins.max() if len(wins) > 0 else 0,
            largest_loss=losses.min() if len(losses) > 0 else 0,
            equity_curve=equity,
            returns=returns,
            positions=positions,
            drawdowns=drawdown,
            trades=trades_df,
            daily_stats=self._compute_daily_stats(equity, returns),
        )

    def _build_trades_df(self) -> pd.DataFrame:
        """Build DataFrame of trades with PnL."""
        if not self.trade_history:
            return pd.DataFrame()

        trades = []
        position = 0
        avg_cost = 0

        for fill in self.trade_history:
            entry_exit = "entry" if position == 0 else "exit"
            pnl = 0

            if fill.side > 0:  # Buy
                if position >= 0:
                    entry_exit = "entry" if position == 0 else "add"
                else:
                    pnl = min(fill.quantity, abs(position)) * (avg_cost - fill.price)
                    entry_exit = "cover"
            else:  # Sell
                if position <= 0:
                    entry_exit = "entry" if position == 0 else "add"
                else:
                    pnl = min(fill.quantity, position) * (fill.price - avg_cost)
                    entry_exit = "close"

            trades.append({
                "timestamp": fill.timestamp,
                "side": "buy" if fill.side > 0 else "sell",
                "price": fill.price,
                "quantity": fill.quantity,
                "commission": fill.commission,
                "slippage": fill.slippage,
                "type": entry_exit,
                "pnl": pnl - fill.commission,
            })

            # Update tracking
            position += fill.side * fill.quantity

        return pd.DataFrame(trades)

    def _compute_daily_stats(
        self,
        equity: pd.Series,
        returns: pd.Series
    ) -> pd.DataFrame:
        """Compute daily statistics."""
        # This is simplified - in practice would group by date
        return pd.DataFrame({
            "equity": [equity.iloc[-1] if len(equity) > 0 else 0],
            "return": [returns.sum() if len(returns) > 0 else 0],
            "trades": [len(self.trade_history)],
        })
