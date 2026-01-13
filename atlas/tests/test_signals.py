"""Tests for the signal generation and validation module."""

import numpy as np
import pandas as pd
import pytest

from atlas.signals.alpha import AlphaSignal, AlphaConfig, AlphaResult
from atlas.signals.validation import (
    WalkForwardValidator,
    WalkForwardConfig,
    FoldResult,
    compute_information_coefficient,
)


class TestAlphaConfig:
    """Tests for alpha configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AlphaConfig()
        assert config.name == "default_alpha"
        assert config.horizon == 10
        assert config.model_type == "ridge"

    def test_custom_config(self):
        """Test custom configuration."""
        config = AlphaConfig(
            name="momentum_alpha",
            horizon=5,
            model_type="gbm",
            n_estimators=50,
        )
        assert config.name == "momentum_alpha"
        assert config.horizon == 5
        assert config.model_type == "gbm"
        assert config.n_estimators == 50


class TestAlphaSignal:
    """Tests for alpha signal generation."""

    def test_alpha_signal_creation(self):
        """Test creating an alpha signal."""
        config = AlphaConfig(name="test_alpha", model_type="ridge")
        signal = AlphaSignal(config)
        assert signal.config.name == "test_alpha"
        assert not signal._is_fitted

    def test_alpha_signal_fit(self):
        """Test fitting an alpha signal."""
        np.random.seed(42)
        n_samples = 500
        n_features = 5

        # Create features and target
        features = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"feature_{i}" for i in range(n_features)]
        )
        # Create target with some signal
        true_weights = np.random.randn(n_features)
        target = pd.Series(features.values @ true_weights + np.random.randn(n_samples) * 0.5)

        config = AlphaConfig(model_type="ridge")
        signal = AlphaSignal(config)
        result = signal.fit(features, target)

        assert isinstance(result, AlphaResult)
        assert signal._is_fitted
        assert len(signal.feature_names) == n_features

    def test_alpha_signal_predict(self):
        """Test prediction with alpha signal."""
        np.random.seed(42)
        n_samples = 500
        n_features = 5

        features = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"feature_{i}" for i in range(n_features)]
        )
        target = pd.Series(np.random.randn(n_samples))

        config = AlphaConfig(model_type="ridge")
        signal = AlphaSignal(config)
        signal.fit(features, target)

        new_features = pd.DataFrame(
            np.random.randn(50, n_features),
            columns=[f"feature_{i}" for i in range(n_features)]
        )
        predictions = signal.predict(new_features)

        assert len(predictions) == 50

    def test_alpha_signal_feature_importance(self):
        """Test feature importance calculation."""
        np.random.seed(42)
        n_samples = 500
        n_features = 5

        features = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"feature_{i}" for i in range(n_features)]
        )
        target = pd.Series(np.random.randn(n_samples))

        config = AlphaConfig(model_type="gbm", n_estimators=10, max_depth=2)
        signal = AlphaSignal(config)
        signal.fit(features, target)

        top_features = signal.get_top_features(n=3)
        assert len(top_features) == 3
        assert all(isinstance(f[0], str) for f in top_features)
        assert all(isinstance(f[1], (int, float)) for f in top_features)

    def test_alpha_result_structure(self):
        """Test AlphaResult dataclass."""
        result = AlphaResult(
            train_ic=0.1,
            val_ic=0.08,
            train_r2=0.05,
            val_r2=0.03,
            feature_importance={"f1": 0.5, "f2": 0.5},
            decay_half_life=5,
            decay_profile=None,
        )
        assert result.train_ic == 0.1
        assert result.val_ic == 0.08


class TestWalkForwardConfig:
    """Tests for walk-forward configuration."""

    def test_default_config(self):
        """Test default configuration."""
        config = WalkForwardConfig()
        assert config.train_window == 10000
        assert config.test_window == 1000
        assert config.step_size == 500

    def test_custom_config(self):
        """Test custom configuration."""
        config = WalkForwardConfig(
            train_window=5000,
            test_window=500,
            step_size=250,
            expanding=True,
        )
        assert config.train_window == 5000
        assert config.expanding is True


class TestWalkForwardValidator:
    """Tests for walk-forward validation."""

    def test_validator_creation(self):
        """Test creating a validator."""
        config = WalkForwardConfig(
            train_window=1000,
            test_window=200,
            step_size=100,
        )
        validator = WalkForwardValidator(config)
        assert validator.config.train_window == 1000
        assert validator.config.test_window == 200

    def test_split_generation(self):
        """Test generating train/test splits."""
        config = WalkForwardConfig(
            train_window=100,
            test_window=20,
            step_size=20,
            min_train_samples=50,
        )
        validator = WalkForwardValidator(config)

        # Need enough samples for train + test
        n_samples = 200
        splits = list(validator.split(n_samples))

        assert len(splits) >= 1

        for train_idx, test_idx in splits:
            # Train should come before test (temporal ordering)
            assert train_idx.max() < test_idx.min()
            # No overlap
            assert len(set(train_idx) & set(test_idx)) == 0

    def test_validate(self):
        """Test full validation."""
        np.random.seed(42)
        from sklearn.linear_model import Ridge

        n_samples = 2000
        n_features = 5

        features = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"feature_{i}" for i in range(n_features)]
        )
        target = pd.Series(np.random.randn(n_samples))

        config = WalkForwardConfig(
            train_window=500,
            test_window=100,
            step_size=100,
            min_train_samples=100,
        )
        validator = WalkForwardValidator(config)
        model = Ridge()

        results = validator.validate(model, features, target)

        assert "n_folds" in results
        assert "mean_ic" in results
        assert "mean_accuracy" in results
        assert results["n_folds"] > 0

    def test_get_results_df(self):
        """Test getting results as DataFrame."""
        np.random.seed(42)
        from sklearn.linear_model import Ridge

        n_samples = 2000
        n_features = 5

        features = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"feature_{i}" for i in range(n_features)]
        )
        target = pd.Series(np.random.randn(n_samples))

        config = WalkForwardConfig(
            train_window=500,
            test_window=100,
            step_size=100,
            min_train_samples=100,
        )
        validator = WalkForwardValidator(config)
        model = Ridge()
        validator.validate(model, features, target)

        df = validator.get_results_df()
        assert isinstance(df, pd.DataFrame)
        if len(df) > 0:
            assert "ic" in df.columns
            assert "accuracy" in df.columns


class TestInformationCoefficient:
    """Tests for information coefficient calculation."""

    def test_ic_calculation(self):
        """Test IC (rank correlation) calculation."""
        # Perfect prediction
        predictions = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        actuals = np.array([0.1, 0.2, 0.3, 0.4, 0.5])

        ic = compute_information_coefficient(predictions, actuals)
        assert np.isclose(ic, 1.0)  # Perfect rank correlation

    def test_ic_negative_correlation(self):
        """Test IC with negative correlation."""
        predictions = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
        actuals = np.array([0.1, 0.2, 0.3, 0.4, 0.5])

        ic = compute_information_coefficient(predictions, actuals)
        assert np.isclose(ic, -1.0)  # Perfect negative correlation

    def test_ic_no_correlation(self):
        """Test IC with no correlation."""
        np.random.seed(42)
        predictions = np.random.randn(100)
        actuals = np.random.randn(100)

        ic = compute_information_coefficient(predictions, actuals)
        # Random data should have IC close to 0
        assert abs(ic) < 0.3
