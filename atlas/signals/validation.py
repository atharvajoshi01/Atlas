"""Walk-forward validation framework for time series."""

from dataclasses import dataclass
from typing import Any, Generator
import numpy as np
import pandas as pd


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward validation."""

    train_window: int = 10000  # Training window size (samples)
    test_window: int = 1000    # Test window size (samples)
    step_size: int = 500       # Step between folds
    min_train_samples: int = 1000
    expanding: bool = False    # If True, train window expands; if False, rolling


@dataclass
class FoldResult:
    """Results from a single validation fold."""

    fold: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    ic: float
    accuracy: float
    hit_rate: float
    sharpe: float
    n_train: int
    n_test: int
    predictions: np.ndarray | None = None
    actuals: np.ndarray | None = None


class WalkForwardValidator:
    """Walk-forward cross-validation for time series.

    Maintains temporal order and avoids look-ahead bias.
    Essential for realistic evaluation of trading signals.

    Example:
        config = WalkForwardConfig(train_window=10000, test_window=1000)
        validator = WalkForwardValidator(config)

        results = validator.validate(model, features_df, target_series)
        print(f"Mean IC: {results['mean_ic']:.4f}")
    """

    def __init__(self, config: WalkForwardConfig | None = None):
        """Initialize validator.

        Args:
            config: Validation configuration.
        """
        self.config = config or WalkForwardConfig()
        self.results: list[FoldResult] = []

    def split(
        self,
        n_samples: int
    ) -> Generator[tuple[np.ndarray, np.ndarray], None, None]:
        """Generate train/test index splits.

        Args:
            n_samples: Total number of samples.

        Yields:
            Tuples of (train_indices, test_indices).
        """
        config = self.config

        for fold, start in enumerate(range(
            0,
            n_samples - config.train_window - config.test_window + 1,
            config.step_size
        )):
            if config.expanding:
                train_start = 0
            else:
                train_start = start

            train_end = start + config.train_window
            test_start = train_end
            test_end = min(test_start + config.test_window, n_samples)

            train_idx = np.arange(train_start, train_end)
            test_idx = np.arange(test_start, test_end)

            if len(train_idx) >= config.min_train_samples:
                yield train_idx, test_idx

    def validate(
        self,
        model,
        features: pd.DataFrame,
        target: pd.Series,
        fit_params: dict[str, Any] | None = None,
        store_predictions: bool = False
    ) -> dict[str, Any]:
        """Run walk-forward validation.

        Args:
            model: Model with fit() and predict() methods.
            features: Feature DataFrame.
            target: Target Series.
            fit_params: Additional parameters for model.fit().
            store_predictions: Whether to store predictions in results.

        Returns:
            Dictionary with aggregated metrics.
        """
        fit_params = fit_params or {}
        self.results = []

        for fold, (train_idx, test_idx) in enumerate(self.split(len(features))):
            X_train = features.iloc[train_idx]
            y_train = target.iloc[train_idx]
            X_test = features.iloc[test_idx]
            y_test = target.iloc[test_idx]

            # Handle NaN values
            train_mask = ~(X_train.isna().any(axis=1) | y_train.isna())
            test_mask = ~(X_test.isna().any(axis=1) | y_test.isna())

            X_train_clean = X_train[train_mask]
            y_train_clean = y_train[train_mask]
            X_test_clean = X_test[test_mask]
            y_test_clean = y_test[test_mask]

            if len(X_train_clean) < self.config.min_train_samples:
                continue

            # Fit model
            model.fit(X_train_clean, y_train_clean, **fit_params)

            # Predict
            predictions = model.predict(X_test_clean)
            actuals = y_test_clean.values

            # Calculate metrics
            result = self._compute_fold_metrics(
                fold=fold,
                train_idx=train_idx,
                test_idx=test_idx,
                predictions=predictions,
                actuals=actuals,
                store_predictions=store_predictions
            )
            self.results.append(result)

        return self._aggregate_results()

    def _compute_fold_metrics(
        self,
        fold: int,
        train_idx: np.ndarray,
        test_idx: np.ndarray,
        predictions: np.ndarray,
        actuals: np.ndarray,
        store_predictions: bool
    ) -> FoldResult:
        """Compute metrics for a single fold."""
        # Information coefficient
        ic = np.corrcoef(predictions, actuals)[0, 1] if len(predictions) > 1 else 0.0

        # Directional accuracy
        pred_direction = np.sign(predictions)
        actual_direction = np.sign(actuals)
        accuracy = (pred_direction == actual_direction).mean()

        # Hit rate (correct sign predictions)
        hit_rate = ((predictions * actuals) > 0).mean()

        # Simplified Sharpe (assuming predictions are positions)
        returns = predictions * actuals
        sharpe = returns.mean() / (returns.std() + 1e-10) * np.sqrt(252)

        return FoldResult(
            fold=fold,
            train_start=int(train_idx[0]),
            train_end=int(train_idx[-1]),
            test_start=int(test_idx[0]),
            test_end=int(test_idx[-1]),
            ic=ic,
            accuracy=accuracy,
            hit_rate=hit_rate,
            sharpe=sharpe,
            n_train=len(train_idx),
            n_test=len(test_idx),
            predictions=predictions if store_predictions else None,
            actuals=actuals if store_predictions else None
        )

    def _aggregate_results(self) -> dict[str, Any]:
        """Aggregate results across all folds."""
        if not self.results:
            return {"error": "No valid folds"}

        ics = [r.ic for r in self.results]
        accuracies = [r.accuracy for r in self.results]
        hit_rates = [r.hit_rate for r in self.results]
        sharpes = [r.sharpe for r in self.results]

        return {
            "n_folds": len(self.results),
            "mean_ic": np.nanmean(ics),
            "std_ic": np.nanstd(ics),
            "min_ic": np.nanmin(ics),
            "max_ic": np.nanmax(ics),
            "mean_accuracy": np.nanmean(accuracies),
            "mean_hit_rate": np.nanmean(hit_rates),
            "mean_sharpe": np.nanmean(sharpes),
            "std_sharpe": np.nanstd(sharpes),
            "ic_positive_rate": (np.array(ics) > 0).mean(),
            "fold_results": self.results,
        }

    def get_results_df(self) -> pd.DataFrame:
        """Get results as DataFrame."""
        if not self.results:
            return pd.DataFrame()

        return pd.DataFrame([
            {
                "fold": r.fold,
                "train_start": r.train_start,
                "train_end": r.train_end,
                "test_start": r.test_start,
                "test_end": r.test_end,
                "ic": r.ic,
                "accuracy": r.accuracy,
                "hit_rate": r.hit_rate,
                "sharpe": r.sharpe,
                "n_train": r.n_train,
                "n_test": r.n_test,
            }
            for r in self.results
        ])

    def analyze_ic_by_regime(
        self,
        regime_labels: pd.Series
    ) -> pd.DataFrame:
        """Analyze IC performance by market regime.

        Args:
            regime_labels: Series with regime labels aligned to test periods.

        Returns:
            DataFrame with IC by regime.
        """
        if not self.results or not all(r.actuals is not None for r in self.results):
            raise ValueError("Must run validate() with store_predictions=True first")

        regime_ics = {}

        for result in self.results:
            test_regimes = regime_labels.iloc[result.test_start:result.test_end + 1]

            for regime in test_regimes.unique():
                mask = test_regimes == regime
                if mask.sum() < 10:
                    continue

                regime_pred = result.predictions[mask.values[:len(result.predictions)]]
                regime_actual = result.actuals[mask.values[:len(result.actuals)]]

                ic = np.corrcoef(regime_pred, regime_actual)[0, 1]

                if regime not in regime_ics:
                    regime_ics[regime] = []
                regime_ics[regime].append(ic)

        return pd.DataFrame([
            {
                "regime": regime,
                "mean_ic": np.mean(ics),
                "std_ic": np.std(ics),
                "n_folds": len(ics),
            }
            for regime, ics in regime_ics.items()
        ])

    def __repr__(self) -> str:
        return (f"WalkForwardValidator(train={self.config.train_window}, "
                f"test={self.config.test_window}, step={self.config.step_size})")


def compute_information_coefficient(
    predictions: np.ndarray,
    actuals: np.ndarray
) -> float:
    """Compute information coefficient (rank correlation).

    Args:
        predictions: Predicted values.
        actuals: Actual values.

    Returns:
        Spearman rank correlation.
    """
    from scipy.stats import spearmanr
    return spearmanr(predictions, actuals)[0]


def compute_ic_decay(
    predictions: np.ndarray,
    returns: pd.DataFrame,
    max_horizon: int = 20
) -> pd.DataFrame:
    """Compute IC decay across horizons.

    Args:
        predictions: Signal predictions.
        returns: DataFrame with forward returns at different horizons.
        max_horizon: Maximum horizon to analyze.

    Returns:
        DataFrame with IC at each horizon.
    """
    decay_data = []

    for h in range(1, max_horizon + 1):
        col = f"fwd_ret_{h}"
        if col in returns.columns:
            ic = compute_information_coefficient(predictions, returns[col].values)
            decay_data.append({"horizon": h, "ic": ic})

    return pd.DataFrame(decay_data)
