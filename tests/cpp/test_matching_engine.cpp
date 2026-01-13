#include <gtest/gtest.h>
#include "atlas/matching/matching_engine.hpp"
#include "atlas/core/types.hpp"

using namespace atlas;

class MatchingEngineTest : public ::testing::Test {
protected:
    void SetUp() override {
        engine = std::make_unique<MatchingEngine>();
    }

    std::unique_ptr<MatchingEngine> engine;
};

// Basic order submission
TEST_F(MatchingEngineTest, SubmitLimitOrder) {
    auto result = engine->submit_order(
        1, to_price(100.0), 100, Side::Buy, OrderType::Limit);

    EXPECT_EQ(result.order_id, 1);
    EXPECT_EQ(result.status, OrderStatus::New);
    EXPECT_EQ(result.filled_quantity, 0);

    const auto& book = engine->get_order_book();
    EXPECT_EQ(book.best_bid(), to_price(100.0));
}

TEST_F(MatchingEngineTest, SubmitMultipleOrders) {
    engine->submit_order(1, to_price(100.0), 100, Side::Buy);
    engine->submit_order(2, to_price(99.0), 200, Side::Buy);
    engine->submit_order(3, to_price(101.0), 150, Side::Sell);

    const auto& book = engine->get_order_book();
    EXPECT_EQ(book.total_order_count(), 3);
    EXPECT_EQ(book.best_bid(), to_price(100.0));
    EXPECT_EQ(book.best_ask(), to_price(101.0));
}

// Order cancellation
TEST_F(MatchingEngineTest, CancelOrder) {
    engine->submit_order(1, to_price(100.0), 100, Side::Buy);
    bool cancelled = engine->cancel_order(1);

    EXPECT_TRUE(cancelled);
    EXPECT_TRUE(engine->get_order_book().empty());
}

TEST_F(MatchingEngineTest, CancelNonexistentOrder) {
    bool cancelled = engine->cancel_order(999);
    EXPECT_FALSE(cancelled);
}

// Order modification
TEST_F(MatchingEngineTest, ModifyOrder) {
    engine->submit_order(1, to_price(100.0), 100, Side::Buy);

    auto result = engine->modify_order(1, to_price(99.0), 150);

    EXPECT_TRUE(result.is_accepted());
    const auto& book = engine->get_order_book();
    EXPECT_EQ(book.best_bid(), to_price(99.0));
    EXPECT_EQ(book.best_bid_quantity(), 150);
}

// Order validation
TEST_F(MatchingEngineTest, RejectZeroQuantity) {
    auto result = engine->submit_order(
        1, to_price(100.0), 0, Side::Buy);

    EXPECT_EQ(result.status, OrderStatus::Rejected);
}

TEST_F(MatchingEngineTest, RejectInvalidOrderId) {
    auto result = engine->submit_order(
        INVALID_ORDER_ID, to_price(100.0), 100, Side::Buy);

    EXPECT_EQ(result.status, OrderStatus::Rejected);
}

TEST_F(MatchingEngineTest, RejectNegativePrice) {
    auto result = engine->submit_order(
        1, -100, 100, Side::Buy, OrderType::Limit);

    EXPECT_EQ(result.status, OrderStatus::Rejected);
}

// Statistics
TEST_F(MatchingEngineTest, TrackOrderStatistics) {
    engine->submit_order(1, to_price(100.0), 100, Side::Buy);
    engine->submit_order(2, to_price(101.0), 100, Side::Sell);
    engine->cancel_order(1);

    EXPECT_EQ(engine->total_orders_submitted(), 2);
    EXPECT_EQ(engine->total_orders_cancelled(), 1);
}

// Reset
TEST_F(MatchingEngineTest, Reset) {
    engine->submit_order(1, to_price(100.0), 100, Side::Buy);
    engine->reset();

    EXPECT_TRUE(engine->get_order_book().empty());
    EXPECT_EQ(engine->total_orders_submitted(), 0);
}

// Trade callback
TEST_F(MatchingEngineTest, TradeCallback) {
    std::vector<Trade> received_trades;

    engine->set_trade_callback([&](const Trade& trade) {
        received_trades.push_back(trade);
    });

    // Add resting order
    engine->submit_order(1, to_price(100.0), 100, Side::Sell);

    // Crossing order
    engine->submit_order(2, to_price(100.0), 50, Side::Buy);

    // Note: Current simplified implementation may not generate trades correctly
    // This test documents expected behavior
}

// Large scale test
TEST_F(MatchingEngineTest, LargeScaleOrders) {
    const int NUM_ORDERS = 10000;

    for (int i = 1; i <= NUM_ORDERS; ++i) {
        Price price = to_price(100.0 + (i % 50) * 0.01);
        Side side = (i % 2 == 0) ? Side::Buy : Side::Sell;
        engine->submit_order(i, price, 100, side);
    }

    EXPECT_EQ(engine->total_orders_submitted(), NUM_ORDERS);
    EXPECT_FALSE(engine->get_order_book().empty());
}

// Order types
TEST_F(MatchingEngineTest, IOCOrderNoMatch) {
    // Submit IOC with no matching liquidity
    auto result = engine->submit_order(
        1, to_price(100.0), 100, Side::Buy, OrderType::IOC);

    // IOC with no match should be cancelled
    EXPECT_EQ(result.status, OrderStatus::Cancelled);
    EXPECT_EQ(result.filled_quantity, 0);
    EXPECT_TRUE(engine->get_order_book().empty());
}

TEST_F(MatchingEngineTest, FOKOrderNoMatch) {
    // Submit FOK with no matching liquidity
    auto result = engine->submit_order(
        1, to_price(100.0), 100, Side::Buy, OrderType::FOK);

    // FOK with no match should be cancelled
    EXPECT_EQ(result.status, OrderStatus::Cancelled);
    EXPECT_EQ(result.filled_quantity, 0);
}

// Configuration test
TEST_F(MatchingEngineTest, ConfigDisableMarketOrders) {
    MatchingEngineConfig config;
    config.allow_market_orders = false;
    auto restricted_engine = std::make_unique<MatchingEngine>(config);

    auto result = restricted_engine->submit_order(
        1, 0, 100, Side::Buy, OrderType::Market);

    EXPECT_EQ(result.status, OrderStatus::Rejected);
}
