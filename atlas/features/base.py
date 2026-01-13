"""Base class for feature generators."""

from abc import ABC, abstractmethod
from typing import Any
import numpy as np


class FeatureGenerator(ABC):
    """Abstract base class for Atlas feature generators.

    All feature generators should inherit from this class and implement
    the required abstract methods.

    Attributes:
        lookback_window: Number of historical observations to consider.
        update_frequency: How often to recompute features (1 = every tick).
    """

    def __init__(
        self,
        lookback_window: int = 100,
        update_frequency: int = 1,
    ):
        """Initialize the feature generator.

        Args:
            lookback_window: Number of historical observations for rolling calculations.
            update_frequency: Recompute features every N updates.
        """
        self.lookback_window = lookback_window
        self.update_frequency = update_frequency
        self._update_count = 0
        self._cache: dict[str, Any] = {}
        self._last_features: np.ndarray | None = None

    @property
    @abstractmethod
    def feature_names(self) -> list[str]:
        """Return list of feature names this generator produces."""
        pass

    @property
    def num_features(self) -> int:
        """Return the number of features produced."""
        return len(self.feature_names)

    @abstractmethod
    def compute(self, state: dict[str, Any]) -> np.ndarray:
        """Compute features from current market state.

        Args:
            state: Dictionary containing market state data.
                   Expected keys depend on the specific generator.

        Returns:
            numpy array of computed features.
        """
        pass

    def update(self, state: dict[str, Any]) -> np.ndarray | None:
        """Update features with new market state.

        Uses update_frequency to skip computation when appropriate.

        Args:
            state: Dictionary containing market state data.

        Returns:
            numpy array of features, or None if skipped this update.
        """
        self._update_count += 1

        if self._update_count % self.update_frequency == 0:
            self._last_features = self.compute(state)
            return self._last_features

        return self._last_features

    def reset(self) -> None:
        """Reset internal state and caches."""
        self._update_count = 0
        self._cache.clear()
        self._last_features = None

    def get_feature_dict(self, features: np.ndarray) -> dict[str, float]:
        """Convert feature array to dictionary with names.

        Args:
            features: numpy array of feature values.

        Returns:
            Dictionary mapping feature names to values.
        """
        return dict(zip(self.feature_names, features.tolist()))

    def validate_state(self, state: dict[str, Any], required_keys: list[str]) -> bool:
        """Validate that state contains required keys.

        Args:
            state: Market state dictionary.
            required_keys: List of keys that must be present.

        Returns:
            True if all required keys are present.
        """
        return all(key in state for key in required_keys)
