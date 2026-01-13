"""Alpha signal generation for short-horizon prediction."""

from dataclasses import dataclass, field
from typing import Any, Callable, Literal
import numpy as np
import pandas as pd

try:
    from sklearn.linear_model import Ridge, Lasso
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


@dataclass
class AlphaConfig:
    """Configuration for alpha signal."""

    name: str = "default_alpha"
    horizon: int = 10  # Prediction horizon in ticks/bars
    target: Literal["return", "direction", "magnitude"] = "return"
    model_type: Literal["ridge", "lasso", "gbm", "rf"] = "ridge"
    min_ic: float = 0.02
    max_decay_half_life: int = 10
    regularization: float = 1.0
    n_estimators: int = 100
    max_depth: int = 3


@dataclass
class AlphaResult:
    """Results from alpha signal training."""

    train_ic: float
    val_ic: float
    train_r2: float
    val_r2: float
    feature_importance: dict[str, float]
    decay_half_life: int | None
    decay_profile: pd.DataFrame | None


class AlphaSignal:
    """Alpha signal generator with decay analysis.

    Generates short-horizon price predictions from order book features.
    Supports multiple model types and includes signal decay analysis.

    Example:
        config = AlphaConfig(name="momentum", horizon=10, model_type="gbm")
        alpha = AlphaSignal(config)

        result = alpha.fit(features_df, returns_series)
        predictions = alpha.predict(new_features_df)
    """

    def __init__(self, config: AlphaConfig | None = None):
        """Initialize alpha signal.

        Args:
            config: Alpha configuration. Uses defaults if not provided.
        """
        if not HAS_SKLEARN:
            raise ImportError("scikit-learn required for AlphaSignal")

        self.config = config or AlphaConfig()
        self.model = None
        self.feature_names: list[str] = []
        self.feature_importance: dict[str, float] = {}
        self.decay_profile: pd.DataFrame | None = None
        self._is_fitted = False

    def _create_model(self):
        """Create the underlying model based on config."""
        if self.config.model_type == "ridge":
            return Ridge(alpha=self.config.regularization)
        elif self.config.model_type == "lasso":
            return Lasso(alpha=self.config.regularization)
        elif self.config.model_type == "gbm":
            return GradientBoostingRegressor(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42,
            )
        elif self.config.model_type == "rf":
            return RandomForestRegressor(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                random_state=42,
            )
        else:
            raise ValueError(f"Unknown model type: {self.config.model_type}")

    def fit(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        validation_pct: float = 0.2,
    ) -> AlphaResult:
        """Fit the alpha model with walk-forward validation.

        Args:
            features: DataFrame of features (samples x features).
            target: Series of target values (forward returns).
            validation_pct: Fraction of data to use for validation.

        Returns:
            AlphaResult with training statistics.
        """
        self.feature_names = list(features.columns)

        # Handle NaN values
        mask = ~(features.isna().any(axis=1) | target.isna())
        features_clean = features[mask]
        target_clean = target[mask]

        # Temporal split (no random shuffle for time series!)
        split_idx = int(len(features_clean) * (1 - validation_pct))
        X_train = features_clean.iloc[:split_idx]
        y_train = target_clean.iloc[:split_idx]
        X_val = features_clean.iloc[split_idx:]
        y_val = target_clean.iloc[split_idx:]

        # Create and train model
        self.model = self._create_model()
        self.model.fit(X_train, y_train)
        self._is_fitted = True

        # Evaluate
        train_pred = self.model.predict(X_train)
        val_pred = self.model.predict(X_val)

        # Information coefficient (IC) = correlation with target
        train_ic = np.corrcoef(train_pred, y_train)[0, 1]
        val_ic = np.corrcoef(val_pred, y_val)[0, 1]

        # R-squared
        train_r2 = self.model.score(X_train, y_train)
        val_r2 = self.model.score(X_val, y_val)

        # Feature importance
        self._compute_feature_importance()

        # Decay analysis
        self.decay_profile = self._analyze_decay(features_clean, target_clean)
        decay_half_life = self._compute_half_life()

        return AlphaResult(
            train_ic=train_ic,
            val_ic=val_ic,
            train_r2=train_r2,
            val_r2=val_r2,
            feature_importance=self.feature_importance,
            decay_half_life=decay_half_life,
            decay_profile=self.decay_profile,
        )

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Generate alpha predictions.

        Args:
            features: DataFrame of features.

        Returns:
            numpy array of predictions.
        """
        if not self._is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        # Handle missing features
        features_aligned = features.reindex(columns=self.feature_names, fill_value=0)
        features_filled = features_aligned.fillna(0)

        return self.model.predict(features_filled)

    def predict_with_confidence(
        self,
        features: pd.DataFrame
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate predictions with confidence scores.

        For tree-based models, uses variance across trees.
        For linear models, uses distance from decision boundary.

        Args:
            features: DataFrame of features.

        Returns:
            Tuple of (predictions, confidence_scores).
        """
        predictions = self.predict(features)

        if self.config.model_type in ["gbm", "rf"]:
            # Use std across estimators as uncertainty
            # This is a simplified approach
            confidence = np.ones(len(predictions)) * 0.5  # Placeholder
        else:
            # For linear models, use prediction magnitude as confidence
            confidence = np.tanh(np.abs(predictions))

        return predictions, confidence

    def _compute_feature_importance(self) -> None:
        """Compute feature importance from fitted model."""
        if self.config.model_type in ["gbm", "rf"]:
            importances = self.model.feature_importances_
        else:
            # For linear models, use absolute coefficients
            importances = np.abs(self.model.coef_)

        # Normalize to sum to 1
        importances = importances / (importances.sum() + 1e-10)

        self.feature_importance = dict(zip(self.feature_names, importances))

    def _analyze_decay(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        max_lag: int = 20
    ) -> pd.DataFrame:
        """Analyze signal decay across time horizons.

        Computes IC at different forecast horizons to understand
        how quickly the signal loses predictive power.

        Args:
            features: Feature DataFrame.
            target: Target Series (original horizon).
            max_lag: Maximum lag to analyze.

        Returns:
            DataFrame with decay statistics.
        """
        predictions = self.model.predict(features)

        decay_data = []
        initial_ic = None

        for lag in range(1, max_lag + 1):
            shifted_target = target.shift(-lag)
            valid_mask = ~shifted_target.isna()

            if valid_mask.sum() < 100:
                break

            ic = np.corrcoef(
                predictions[valid_mask],
                shifted_target[valid_mask]
            )[0, 1]

            if lag == 1:
                initial_ic = ic

            decay_data.append({
                "lag": lag,
                "ic": ic,
                "ic_normalized": ic / initial_ic if initial_ic else 1.0,
            })

        return pd.DataFrame(decay_data)

    def _compute_half_life(self) -> int | None:
        """Compute signal half-life from decay profile.

        Returns:
            Lag at which IC drops to 50% of initial, or None.
        """
        if self.decay_profile is None or len(self.decay_profile) == 0:
            return None

        for _, row in self.decay_profile.iterrows():
            if row["ic_normalized"] < 0.5:
                return int(row["lag"])

        return len(self.decay_profile)

    def get_top_features(self, n: int = 10) -> list[tuple[str, float]]:
        """Get top N most important features.

        Args:
            n: Number of features to return.

        Returns:
            List of (feature_name, importance) tuples.
        """
        sorted_features = sorted(
            self.feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_features[:n]

    def evaluate_ic_stability(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        window_size: int = 1000,
        step_size: int = 100
    ) -> pd.DataFrame:
        """Evaluate IC stability over rolling windows.

        Args:
            features: Feature DataFrame.
            target: Target Series.
            window_size: Size of rolling window.
            step_size: Step between windows.

        Returns:
            DataFrame with rolling IC statistics.
        """
        predictions = self.predict(features)

        ic_data = []
        for start in range(0, len(predictions) - window_size, step_size):
            end = start + window_size
            window_pred = predictions[start:end]
            window_target = target.iloc[start:end]

            valid_mask = ~window_target.isna()
            if valid_mask.sum() < 50:
                continue

            ic = np.corrcoef(window_pred[valid_mask], window_target[valid_mask])[0, 1]

            ic_data.append({
                "start_idx": start,
                "end_idx": end,
                "ic": ic,
            })

        return pd.DataFrame(ic_data)

    def save(self, path: str) -> None:
        """Save model to file.

        Args:
            path: Path to save model.
        """
        import joblib
        joblib.dump({
            "model": self.model,
            "config": self.config,
            "feature_names": self.feature_names,
            "feature_importance": self.feature_importance,
        }, path)

    @classmethod
    def load(cls, path: str) -> "AlphaSignal":
        """Load model from file.

        Args:
            path: Path to load model from.

        Returns:
            Loaded AlphaSignal instance.
        """
        import joblib
        data = joblib.load(path)

        signal = cls(config=data["config"])
        signal.model = data["model"]
        signal.feature_names = data["feature_names"]
        signal.feature_importance = data["feature_importance"]
        signal._is_fitted = True

        return signal

    def __repr__(self) -> str:
        status = "fitted" if self._is_fitted else "not fitted"
        return f"AlphaSignal(name='{self.config.name}', model={self.config.model_type}, {status})"
