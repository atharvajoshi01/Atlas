"""Tests for the monitoring and drift detection module."""

import numpy as np
import pandas as pd
import pytest

from atlas.monitoring.drift import FeatureDriftDetector, DriftResult


class TestPSI:
    """Tests for Population Stability Index calculation."""

    def test_psi_identical_distributions(self):
        """Test PSI with identical distributions."""
        np.random.seed(42)
        detector = FeatureDriftDetector()
        reference = np.random.normal(0, 1, 10000)
        current = np.random.normal(0, 1, 10000)

        psi = detector.calculate_psi(reference, current)
        # Identical distributions should have very low PSI
        assert psi < 0.1

    def test_psi_shifted_distribution(self):
        """Test PSI with shifted distribution."""
        np.random.seed(42)
        detector = FeatureDriftDetector()
        reference = np.random.normal(0, 1, 10000)
        current = np.random.normal(1, 1, 10000)  # Shifted mean

        psi = detector.calculate_psi(reference, current)
        # Shifted distribution should have higher PSI
        assert psi > 0.1

    def test_psi_completely_different(self):
        """Test PSI with very different distributions."""
        np.random.seed(42)
        detector = FeatureDriftDetector()
        reference = np.random.normal(0, 1, 10000)
        current = np.random.normal(5, 0.5, 10000)  # Very different

        psi = detector.calculate_psi(reference, current)
        # Very different distributions should have high PSI
        assert psi > 0.25


class TestKSTest:
    """Tests for Kolmogorov-Smirnov test."""

    def test_ks_identical_distributions(self):
        """Test KS test with identical distributions."""
        np.random.seed(42)
        detector = FeatureDriftDetector()
        reference = np.random.normal(0, 1, 1000)
        current = np.random.normal(0, 1, 1000)

        statistic, p_value = detector.ks_test(reference, current)

        # High p-value means we cannot reject null hypothesis (same distribution)
        assert p_value > 0.05
        assert statistic < 0.1

    def test_ks_different_distributions(self):
        """Test KS test with different distributions."""
        np.random.seed(42)
        detector = FeatureDriftDetector()
        reference = np.random.normal(0, 1, 1000)
        current = np.random.normal(2, 1, 1000)

        statistic, p_value = detector.ks_test(reference, current)

        # Low p-value means distributions are different
        assert p_value < 0.05
        assert statistic > 0.3

    def test_ks_statistic_bounds(self):
        """Test that KS statistic is between 0 and 1."""
        np.random.seed(42)
        detector = FeatureDriftDetector()
        reference = np.random.uniform(0, 1, 500)
        current = np.random.uniform(0.5, 1.5, 500)

        statistic, _ = detector.ks_test(reference, current)

        assert 0 <= statistic <= 1


class TestFeatureDriftDetector:
    """Tests for the feature drift detector."""

    def test_detector_creation(self):
        """Test creating a drift detector."""
        detector = FeatureDriftDetector(
            reference_window=5000,
            current_window=500,
            n_bins=10,
        )
        assert detector.reference_window == 5000
        assert detector.current_window == 500
        assert detector.n_bins == 10

    def test_detect_drift_no_drift(self):
        """Test detecting no drift with similar distributions."""
        np.random.seed(42)

        # Create data with no drift
        n_samples = 12000
        data = pd.DataFrame({
            "feature_1": np.random.normal(0, 1, n_samples),
            "feature_2": np.random.normal(5, 2, n_samples),
        })

        detector = FeatureDriftDetector(reference_window=10000, current_window=1000)
        results = detector.detect_drift(data, ["feature_1", "feature_2"])

        # No significant drift expected
        drifted = [r for r in results if r.is_drifted]
        assert len(drifted) == 0

    def test_detect_drift_with_drift(self):
        """Test detecting drift with shifted distributions."""
        np.random.seed(42)

        # Create data with drift at the end
        n_samples = 12000
        feature_1 = np.concatenate([
            np.random.normal(0, 1, 11000),  # Reference period
            np.random.normal(2, 1, 1000),   # Drifted current period
        ])
        feature_2 = np.random.normal(5, 2, n_samples)  # No drift

        data = pd.DataFrame({
            "feature_1": feature_1,
            "feature_2": feature_2,
        })

        detector = FeatureDriftDetector(reference_window=10000, current_window=1000)
        results = detector.detect_drift(data, ["feature_1", "feature_2"])

        # Feature 1 should show drift
        feature_1_result = next(r for r in results if r.feature_name == "feature_1")
        assert feature_1_result.is_drifted

    def test_drift_result_structure(self):
        """Test DriftResult dataclass structure."""
        from datetime import datetime

        result = DriftResult(
            feature_name="test_feature",
            metric_name="psi",
            value=0.15,
            threshold=0.1,
            is_drifted=True,
            severity="low",
            computed_at=datetime.utcnow(),
        )

        assert result.feature_name == "test_feature"
        assert result.metric_name == "psi"
        assert result.value == 0.15
        assert result.is_drifted is True
        assert result.severity == "low"

    def test_get_summary(self):
        """Test drift summary generation."""
        from datetime import datetime

        detector = FeatureDriftDetector()

        results = [
            DriftResult("f1", "psi", 0.05, 0.1, False, "none", datetime.utcnow()),
            DriftResult("f2", "psi", 0.15, 0.1, True, "low", datetime.utcnow()),
            DriftResult("f3", "psi", 0.30, 0.1, True, "high", datetime.utcnow()),
        ]

        summary = detector.get_summary(results)

        assert summary["total_features"] == 3
        assert summary["drifted_features"] == 2
        assert summary["high_severity"] == 1
        assert "f2" in summary["drifted_names"]
        assert "f3" in summary["drifted_names"]


class TestWassersteinDistance:
    """Tests for Wasserstein distance calculation."""

    def test_wasserstein_identical(self):
        """Test Wasserstein distance for identical distributions."""
        np.random.seed(42)
        detector = FeatureDriftDetector()

        reference = np.random.normal(0, 1, 1000)
        current = np.random.normal(0, 1, 1000)

        distance = detector.wasserstein_distance(reference, current)
        # Should be close to 0 for same distribution
        assert distance < 0.2

    def test_wasserstein_shifted(self):
        """Test Wasserstein distance for shifted distributions."""
        np.random.seed(42)
        detector = FeatureDriftDetector()

        reference = np.random.normal(0, 1, 1000)
        current = np.random.normal(2, 1, 1000)  # Shifted by 2

        distance = detector.wasserstein_distance(reference, current)
        # Distance should reflect the shift
        assert 1.5 < distance < 2.5


class TestModelDrift:
    """Tests for model performance drift detection."""

    def test_detect_model_drift(self):
        """Test detecting model performance drift."""
        np.random.seed(42)
        detector = FeatureDriftDetector()

        # Create predictions and actuals with degrading performance
        n_samples = 5000
        predictions = np.random.randn(n_samples)

        # Actuals correlate well at start, poorly at end
        actuals = np.concatenate([
            predictions[:4000] + np.random.randn(4000) * 0.3,  # Good correlation
            np.random.randn(1000),  # Poor correlation
        ])

        results = detector.detect_model_drift(
            predictions, actuals,
            window_size=500, step_size=100
        )

        assert len(results) > 0
        assert "ic" in results.columns
        assert "accuracy" in results.columns

        # IC should be higher in earlier windows
        early_ic = results.iloc[:10]["ic"].mean()
        late_ic = results.iloc[-10:]["ic"].mean()
        assert early_ic > late_ic
