"""Feature pipeline for combining multiple feature generators."""

from typing import Any
import numpy as np

from atlas.features.base import FeatureGenerator
from atlas.features.orderbook import OrderBookFeatures
from atlas.features.trade import TradeFeatures
from atlas.features.volatility import VolatilityFeatures
from atlas.features.microstructure import MicrostructureFeatures


class FeaturePipeline:
    """Pipeline for computing and managing multiple feature generators.

    Combines multiple feature generators into a single interface,
    handles feature normalization, and provides incremental updates.

    Example:
        pipeline = FeaturePipeline()
        pipeline.add_generator(OrderBookFeatures())
        pipeline.add_generator(TradeFeatures())

        features = pipeline.compute(market_state)
        normalized = pipeline.normalize(features)
    """

    def __init__(
        self,
        normalize: bool = True,
        clip_outliers: bool = True,
        outlier_std: float = 5.0,
    ):
        """Initialize feature pipeline.

        Args:
            normalize: Whether to z-score normalize features.
            clip_outliers: Whether to clip extreme values.
            outlier_std: Number of standard deviations for outlier clipping.
        """
        self.generators: list[FeatureGenerator] = []
        self.normalize_features = normalize
        self.clip_outliers = clip_outliers
        self.outlier_std = outlier_std

        # Running statistics for normalization
        self._feature_means: np.ndarray | None = None
        self._feature_stds: np.ndarray | None = None
        self._feature_count: int = 0

        # Feature name mapping
        self._feature_names: list[str] = []

    @classmethod
    def default(cls) -> "FeaturePipeline":
        """Create a pipeline with default feature generators."""
        pipeline = cls()
        pipeline.add_generator(OrderBookFeatures())
        pipeline.add_generator(TradeFeatures())
        pipeline.add_generator(VolatilityFeatures())
        pipeline.add_generator(MicrostructureFeatures())
        return pipeline

    def add_generator(self, generator: FeatureGenerator) -> None:
        """Add a feature generator to the pipeline."""
        self.generators.append(generator)
        self._feature_names.extend(generator.feature_names)
        self._reset_normalization()

    @property
    def feature_names(self) -> list[str]:
        """Get all feature names."""
        return self._feature_names

    @property
    def num_features(self) -> int:
        """Get total number of features."""
        return len(self._feature_names)

    def compute(self, state: dict[str, Any]) -> np.ndarray:
        """Compute all features from market state.

        Args:
            state: Dictionary containing all required market data.

        Returns:
            numpy array of all feature values.
        """
        features_list = []
        for generator in self.generators:
            features = generator.compute(state)
            features_list.append(features)

        all_features = np.concatenate(features_list)

        # Update normalization statistics
        self._update_statistics(all_features)

        return all_features

    def compute_normalized(self, state: dict[str, Any]) -> np.ndarray:
        """Compute and normalize all features.

        Args:
            state: Dictionary containing all required market data.

        Returns:
            numpy array of normalized feature values.
        """
        features = self.compute(state)
        return self.normalize(features)

    def normalize(self, features: np.ndarray) -> np.ndarray:
        """Normalize feature values using running statistics.

        Args:
            features: Raw feature values.

        Returns:
            Normalized feature values.
        """
        if not self.normalize_features:
            return features

        if self._feature_means is None or self._feature_stds is None:
            return features

        # Z-score normalization
        normalized = (features - self._feature_means) / (self._feature_stds + 1e-8)

        # Clip outliers
        if self.clip_outliers:
            normalized = np.clip(normalized, -self.outlier_std, self.outlier_std)

        # Handle NaN values (forward fill with 0)
        normalized = np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0)

        return normalized

    def get_feature_dict(self, features: np.ndarray) -> dict[str, float]:
        """Convert feature array to dictionary with names."""
        return dict(zip(self._feature_names, features.tolist()))

    def get_feature_importance(
        self,
        feature_importances: np.ndarray
    ) -> dict[str, float]:
        """Map feature importances to feature names."""
        return dict(zip(self._feature_names, feature_importances.tolist()))

    def reset(self) -> None:
        """Reset all generators and normalization statistics."""
        for generator in self.generators:
            generator.reset()
        self._reset_normalization()

    def _reset_normalization(self) -> None:
        """Reset normalization statistics."""
        self._feature_means = None
        self._feature_stds = None
        self._feature_count = 0

    def _update_statistics(self, features: np.ndarray) -> None:
        """Update running mean and std for normalization.

        Uses Welford's online algorithm for numerical stability.
        """
        if not self.normalize_features:
            return

        self._feature_count += 1

        if self._feature_means is None:
            self._feature_means = np.zeros(len(features))
            self._feature_stds = np.ones(len(features))
            self._M2 = np.zeros(len(features))

        # Welford's algorithm
        delta = features - self._feature_means
        self._feature_means += delta / self._feature_count

        delta2 = features - self._feature_means
        self._M2 += delta * delta2

        if self._feature_count > 1:
            variance = self._M2 / (self._feature_count - 1)
            self._feature_stds = np.sqrt(np.maximum(variance, 1e-8))

    def set_normalization_params(
        self,
        means: np.ndarray,
        stds: np.ndarray
    ) -> None:
        """Set normalization parameters from training data.

        Args:
            means: Feature means.
            stds: Feature standard deviations.
        """
        self._feature_means = means.copy()
        self._feature_stds = stds.copy()
        self._feature_count = 1  # Prevent auto-update

    def get_normalization_params(self) -> tuple[np.ndarray | None, np.ndarray | None]:
        """Get current normalization parameters."""
        return self._feature_means, self._feature_stds

    def compute_batch(
        self,
        states: list[dict[str, Any]]
    ) -> np.ndarray:
        """Compute features for a batch of market states.

        Args:
            states: List of market state dictionaries.

        Returns:
            2D numpy array of shape (n_samples, n_features).
        """
        features_batch = []
        for state in states:
            features = self.compute(state)
            features_batch.append(features)
        return np.vstack(features_batch)

    def compute_batch_normalized(
        self,
        states: list[dict[str, Any]]
    ) -> np.ndarray:
        """Compute and normalize features for a batch.

        Args:
            states: List of market state dictionaries.

        Returns:
            2D numpy array of normalized features.
        """
        raw_features = self.compute_batch(states)

        if not self.normalize_features:
            return raw_features

        # Compute batch statistics
        means = np.nanmean(raw_features, axis=0)
        stds = np.nanstd(raw_features, axis=0)

        # Normalize
        normalized = (raw_features - means) / (stds + 1e-8)

        if self.clip_outliers:
            normalized = np.clip(normalized, -self.outlier_std, self.outlier_std)

        return np.nan_to_num(normalized, nan=0.0)

    def __len__(self) -> int:
        """Return number of features."""
        return self.num_features

    def __repr__(self) -> str:
        generator_names = [type(g).__name__ for g in self.generators]
        return f"FeaturePipeline({generator_names}, n_features={self.num_features})"
