"""Feature and prediction drift detection."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
import numpy as np
import pandas as pd


@dataclass
class DriftResult:
    """Result of drift detection for a single feature."""

    feature_name: str
    metric_name: str
    value: float
    threshold: float
    is_drifted: bool
    severity: str  # "none", "low", "medium", "high"
    computed_at: datetime


class FeatureDriftDetector:
    """Detect drift in feature distributions using PSI and statistical tests.

    Population Stability Index (PSI) and Kolmogorov-Smirnov test are used
    to detect distribution shifts between reference and current data.

    Example:
        detector = FeatureDriftDetector()
        results = detector.detect_drift(feature_df, feature_names)
        drifted = [r for r in results if r.is_drifted]
    """

    PSI_THRESHOLDS = {
        "low": 0.1,
        "medium": 0.2,
        "high": 0.25,
    }

    def __init__(
        self,
        reference_window: int = 10000,
        current_window: int = 1000,
        n_bins: int = 10,
    ):
        """Initialize drift detector.

        Args:
            reference_window: Number of samples for reference distribution.
            current_window: Number of samples for current distribution.
            n_bins: Number of bins for PSI calculation.
        """
        self.reference_window = reference_window
        self.current_window = current_window
        self.n_bins = n_bins

    def calculate_psi(
        self,
        reference: np.ndarray,
        current: np.ndarray,
    ) -> float:
        """Calculate Population Stability Index.

        PSI = Σ (current% - reference%) * ln(current% / reference%)

        Args:
            reference: Reference distribution samples.
            current: Current distribution samples.

        Returns:
            PSI value. Higher values indicate more drift.
        """
        # Handle NaN values
        reference = reference[~np.isnan(reference)]
        current = current[~np.isnan(current)]

        if len(reference) < 10 or len(current) < 10:
            return np.nan

        # Create bins from reference data
        _, bin_edges = np.histogram(reference, bins=self.n_bins)

        # Small epsilon to avoid division by zero
        eps = 1e-6

        ref_counts, _ = np.histogram(reference, bins=bin_edges)
        curr_counts, _ = np.histogram(current, bins=bin_edges)

        ref_props = (ref_counts + eps) / (len(reference) + eps * self.n_bins)
        curr_props = (curr_counts + eps) / (len(current) + eps * self.n_bins)

        psi = np.sum((curr_props - ref_props) * np.log(curr_props / ref_props))
        return float(psi)

    def ks_test(
        self,
        reference: np.ndarray,
        current: np.ndarray,
    ) -> tuple[float, float]:
        """Kolmogorov-Smirnov test for distribution shift.

        Args:
            reference: Reference distribution samples.
            current: Current distribution samples.

        Returns:
            Tuple of (statistic, p-value).
        """
        from scipy.stats import ks_2samp

        reference = reference[~np.isnan(reference)]
        current = current[~np.isnan(current)]

        if len(reference) < 10 or len(current) < 10:
            return np.nan, np.nan

        return ks_2samp(reference, current)

    def wasserstein_distance(
        self,
        reference: np.ndarray,
        current: np.ndarray,
    ) -> float:
        """Compute Wasserstein (Earth Mover's) distance.

        Args:
            reference: Reference distribution samples.
            current: Current distribution samples.

        Returns:
            Wasserstein distance.
        """
        from scipy.stats import wasserstein_distance

        reference = reference[~np.isnan(reference)]
        current = current[~np.isnan(current)]

        if len(reference) < 10 or len(current) < 10:
            return np.nan

        return wasserstein_distance(reference, current)

    def detect_drift(
        self,
        data: pd.DataFrame,
        feature_names: list[str] | None = None,
    ) -> list[DriftResult]:
        """Detect drift for all features.

        Args:
            data: DataFrame with feature columns.
            feature_names: Optional list of features to check.

        Returns:
            List of DriftResult for each feature.
        """
        if feature_names is None:
            feature_names = list(data.columns)

        if len(data) < self.reference_window + self.current_window:
            # Not enough data
            return []

        reference_data = data.iloc[
            -self.reference_window - self.current_window:-self.current_window
        ]
        current_data = data.iloc[-self.current_window:]

        results = []
        computed_at = datetime.utcnow()

        for feature in feature_names:
            if feature not in data.columns:
                continue

            reference = reference_data[feature].values
            current = current_data[feature].values

            # Calculate PSI
            psi = self.calculate_psi(reference, current)

            if np.isnan(psi):
                continue

            # Calculate KS test
            ks_stat, ks_pvalue = self.ks_test(reference, current)

            # Determine severity
            if psi < self.PSI_THRESHOLDS["low"] and (np.isnan(ks_pvalue) or ks_pvalue > 0.05):
                severity = "none"
                is_drifted = False
            elif psi < self.PSI_THRESHOLDS["medium"]:
                severity = "low"
                is_drifted = True
            elif psi < self.PSI_THRESHOLDS["high"]:
                severity = "medium"
                is_drifted = True
            else:
                severity = "high"
                is_drifted = True

            results.append(
                DriftResult(
                    feature_name=feature,
                    metric_name="psi",
                    value=psi,
                    threshold=self.PSI_THRESHOLDS["low"],
                    is_drifted=is_drifted,
                    severity=severity,
                    computed_at=computed_at,
                )
            )

        return results

    def get_summary(self, results: list[DriftResult]) -> dict[str, Any]:
        """Summarize drift detection results.

        Args:
            results: List of DriftResult.

        Returns:
            Summary dictionary.
        """
        if not results:
            return {
                "total_features": 0,
                "drifted_features": 0,
                "high_severity": 0,
                "drift_rate": 0,
                "avg_psi": 0,
                "max_psi": 0,
                "drifted_names": [],
            }

        drifted = [r for r in results if r.is_drifted]
        high_severity = [r for r in results if r.severity == "high"]

        return {
            "total_features": len(results),
            "drifted_features": len(drifted),
            "high_severity": len(high_severity),
            "drift_rate": len(drifted) / len(results),
            "avg_psi": np.mean([r.value for r in results]),
            "max_psi": max([r.value for r in results]),
            "drifted_names": [r.feature_name for r in drifted],
        }

    def detect_model_drift(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray,
        window_size: int = 1000,
        step_size: int = 100,
    ) -> pd.DataFrame:
        """Detect drift in model performance over time.

        Args:
            predictions: Model predictions.
            actuals: Actual values.
            window_size: Rolling window size.
            step_size: Step between windows.

        Returns:
            DataFrame with rolling performance metrics.
        """
        results = []

        for start in range(0, len(predictions) - window_size, step_size):
            end = start + window_size
            window_pred = predictions[start:end]
            window_actual = actuals[start:end]

            # IC
            ic = np.corrcoef(window_pred, window_actual)[0, 1]

            # Accuracy
            accuracy = (np.sign(window_pred) == np.sign(window_actual)).mean()

            # MAE
            mae = np.mean(np.abs(window_pred - window_actual))

            results.append({
                "start_idx": start,
                "end_idx": end,
                "ic": ic,
                "accuracy": accuracy,
                "mae": mae,
            })

        return pd.DataFrame(results)
