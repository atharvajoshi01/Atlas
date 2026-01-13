"""Tests for the feature engineering module."""

import numpy as np
import pytest

from atlas.features.orderbook import (
    OrderBookFeatures,
    compute_mid_price,
    compute_spread_bps,
    compute_imbalance,
    compute_weighted_imbalance,
    compute_book_pressure,
    compute_depth_ratio,
    compute_price_impact,
)
from atlas.features.trade import TradeFeatures
from atlas.features.volatility import VolatilityFeatures
from atlas.features.pipeline import FeaturePipeline


class TestOrderBookFunctions:
    """Tests for order book feature computation functions."""

    def test_compute_mid_price(self):
        """Test mid price calculation."""
        mid = compute_mid_price(100.0, 100.1)
        assert np.isclose(mid, 100.05)

    def test_compute_mid_price_invalid(self):
        """Test mid price with invalid input."""
        mid = compute_mid_price(0.0, 100.1)
        assert np.isnan(mid)

    def test_compute_spread_bps(self):
        """Test spread in basis points."""
        spread_bps = compute_spread_bps(100.0, 100.1)
        # spread = 0.1, mid = 100.05, bps = 0.1 / 100.05 * 10000 ~= 10
        assert np.isclose(spread_bps, 10.0, atol=0.1)

    def test_compute_imbalance(self):
        """Test order book imbalance calculation."""
        bid_sizes = np.array([100.0, 200.0, 150.0])
        ask_sizes = np.array([50.0, 75.0, 100.0])

        imbalance = compute_imbalance(bid_sizes, ask_sizes, levels=3)
        # bid_total = 450, ask_total = 225, imbalance = (450 - 225) / (450 + 225) = 0.333
        assert np.isclose(imbalance, 0.333, atol=0.01)

    def test_compute_imbalance_all_bids(self):
        """Test imbalance when all bids."""
        bid_sizes = np.array([100.0, 200.0])
        ask_sizes = np.array([0.0, 0.0])

        imbalance = compute_imbalance(bid_sizes, ask_sizes, levels=2)
        assert np.isclose(imbalance, 1.0)

    def test_compute_imbalance_all_asks(self):
        """Test imbalance when all asks."""
        bid_sizes = np.array([0.0, 0.0])
        ask_sizes = np.array([100.0, 200.0])

        imbalance = compute_imbalance(bid_sizes, ask_sizes, levels=2)
        assert np.isclose(imbalance, -1.0)

    def test_compute_weighted_imbalance(self):
        """Test weighted imbalance (closer levels weighted more)."""
        bid_prices = np.array([100.0, 99.9, 99.8])
        bid_sizes = np.array([100.0, 200.0, 150.0])
        ask_prices = np.array([100.1, 100.2, 100.3])
        ask_sizes = np.array([50.0, 75.0, 100.0])

        weighted_imb = compute_weighted_imbalance(
            bid_prices, bid_sizes, ask_prices, ask_sizes, levels=3
        )
        # Should be positive (more bid pressure)
        assert weighted_imb > 0

    def test_compute_book_pressure(self):
        """Test book pressure calculation."""
        bid_prices = np.array([100.0, 99.9, 99.8])
        bid_sizes = np.array([100.0, 200.0, 150.0])
        ask_prices = np.array([100.1, 100.2, 100.3])
        ask_sizes = np.array([50.0, 75.0, 100.0])

        pressure = compute_book_pressure(
            bid_prices, bid_sizes, ask_prices, ask_sizes, levels=3
        )
        # More bid size = positive pressure
        assert pressure > 0

    def test_compute_depth_ratio(self):
        """Test bid/ask depth ratio."""
        bid_sizes = np.array([100.0, 200.0, 150.0])
        ask_sizes = np.array([50.0, 75.0, 100.0])

        ratio = compute_depth_ratio(bid_sizes, ask_sizes, levels=3)
        # bid_total = 450, ask_total = 225, ratio = 2.0
        assert np.isclose(ratio, 2.0)

    def test_compute_price_impact(self):
        """Test price impact calculation."""
        prices = np.array([100.0, 99.9, 99.8, 99.7, 99.6])
        sizes = np.array([100.0, 100.0, 100.0, 100.0, 100.0])

        impact = compute_price_impact(prices, sizes, 150.0)
        # Should walk through 100 @ 100.0 and 50 @ 99.9
        # VWAP = (100*100 + 50*99.9) / 150 = 99.967
        # Impact from 100.0 to 99.967 is about 3.3 bps
        assert impact > 0


class TestOrderBookFeaturesClass:
    """Tests for OrderBookFeatures class."""

    def test_feature_names(self):
        """Test that feature names are defined."""
        features = OrderBookFeatures()
        assert len(features.feature_names) > 0
        assert "mid_price" in features.feature_names
        assert "spread_bps" in features.feature_names

    def test_compute_features(self):
        """Test computing features from state."""
        features = OrderBookFeatures()

        state = {
            "bid_prices": np.array([100.0, 99.9, 99.8, 99.7, 99.6]),
            "bid_sizes": np.array([100.0, 200.0, 150.0, 300.0, 250.0]),
            "ask_prices": np.array([100.1, 100.2, 100.3, 100.4, 100.5]),
            "ask_sizes": np.array([120.0, 180.0, 200.0, 150.0, 100.0]),
        }

        result = features.compute(state)
        assert isinstance(result, np.ndarray)
        assert len(result) == len(features.feature_names)
        assert not np.all(np.isnan(result))

    def test_compute_empty_book(self):
        """Test computing features with empty book."""
        features = OrderBookFeatures()

        state = {
            "bid_prices": np.array([]),
            "bid_sizes": np.array([]),
            "ask_prices": np.array([]),
            "ask_sizes": np.array([]),
        }

        result = features.compute(state)
        assert np.all(np.isnan(result))


class TestTradeFeatures:
    """Tests for trade-based features."""

    def test_feature_names(self):
        """Test that feature names are defined."""
        features = TradeFeatures()
        assert len(features.feature_names) > 0

    def test_compute_features(self):
        """Test computing trade features."""
        features = TradeFeatures()

        # TradeFeatures expects trade_sizes (not trade_volumes)
        state = {
            "trade_prices": np.array([100.0, 100.1, 99.9, 100.05, 100.02]),
            "trade_sizes": np.array([100.0, 200.0, 150.0, 50.0, 100.0]),
            "trade_sides": np.array([1, 1, -1, 1, -1]),  # 1 = buy, -1 = sell
            "mid_price": 100.0,
        }

        result = features.compute(state)
        assert isinstance(result, np.ndarray)
        assert len(result) == len(features.feature_names)


class TestVolatilityFeatures:
    """Tests for volatility estimators."""

    def test_feature_names(self):
        """Test that feature names are defined."""
        features = VolatilityFeatures()
        assert len(features.feature_names) > 0

    def test_compute_features(self):
        """Test computing volatility features."""
        features = VolatilityFeatures()

        np.random.seed(42)
        n = 100
        prices = 100.0 + np.cumsum(np.random.normal(0, 0.1, n))

        state = {
            "prices": prices,
            "high": prices + np.random.uniform(0, 0.5, n),
            "low": prices - np.random.uniform(0, 0.5, n),
            "open": np.roll(prices, 1),
            "close": prices,
        }

        result = features.compute(state)
        assert isinstance(result, np.ndarray)
        assert len(result) == len(features.feature_names)


class TestFeaturePipeline:
    """Tests for the feature pipeline."""

    def test_pipeline_creation(self):
        """Test creating a default pipeline."""
        pipeline = FeaturePipeline.default()
        assert len(pipeline.generators) > 0

    def test_pipeline_feature_names(self):
        """Test getting feature names from pipeline."""
        pipeline = FeaturePipeline.default()
        names = pipeline.feature_names
        assert len(names) > 0

    def test_pipeline_compute(self):
        """Test computing features through pipeline."""
        pipeline = FeaturePipeline.default()

        # Create mock market state with all required fields
        state = {
            "bid_prices": np.array([100.0, 99.9, 99.8, 99.7, 99.6]),
            "bid_sizes": np.array([100.0, 200.0, 150.0, 300.0, 250.0]),
            "ask_prices": np.array([100.1, 100.2, 100.3, 100.4, 100.5]),
            "ask_sizes": np.array([120.0, 180.0, 200.0, 150.0, 100.0]),
            "trade_prices": np.array([100.0, 100.1, 99.9, 100.05]),
            "trade_sizes": np.array([50.0, 100.0, 75.0, 25.0]),  # Use trade_sizes
            "trade_sides": np.array([1, 1, -1, 1]),
            "mid_price": 100.05,
            "prices": np.array([100.0, 100.1, 99.9, 100.05]),
            "high": np.array([100.5, 100.6, 100.4, 100.55]),
            "low": np.array([99.5, 99.6, 99.4, 99.55]),
            "open": np.array([99.8, 100.0, 100.1, 99.9]),
            "close": np.array([100.0, 100.1, 99.9, 100.05]),
        }

        features = pipeline.compute(state)
        # Pipeline.compute returns numpy array (concatenated features from all generators)
        assert isinstance(features, np.ndarray)
        assert len(features) > 0


class TestImbalanceBounds:
    """Property-based tests for imbalance bounds."""

    def test_imbalance_between_minus_one_and_one(self):
        """Imbalance should always be between -1 and 1."""
        np.random.seed(42)
        for _ in range(100):
            bid_sizes = np.random.uniform(1.0, 1000.0, size=5)
            ask_sizes = np.random.uniform(1.0, 1000.0, size=5)

            imbalance = compute_imbalance(bid_sizes, ask_sizes, levels=5)
            assert -1 <= imbalance <= 1

    def test_mid_price_between_bid_ask(self):
        """Mid price should always be between best bid and best ask."""
        np.random.seed(42)
        for _ in range(100):
            bid_price = np.random.uniform(90.0, 100.0)
            ask_price = np.random.uniform(100.0, 110.0)

            mid = compute_mid_price(bid_price, ask_price)
            assert bid_price <= mid <= ask_price

    def test_spread_non_negative(self):
        """Spread should always be non-negative."""
        np.random.seed(42)
        for _ in range(100):
            bid_price = np.random.uniform(90.0, 100.0)
            ask_price = bid_price + np.random.uniform(0.01, 1.0)

            spread = compute_spread_bps(bid_price, ask_price)
            assert spread >= 0
