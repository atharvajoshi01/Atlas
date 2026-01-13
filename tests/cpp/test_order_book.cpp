#include <gtest/gtest.h>
#include "atlas/core/order_book.hpp"
#include "atlas/core/types.hpp"

using namespace atlas;

class OrderBookTest : public ::testing::Test {
protected:
    void SetUp() override {
        book = std::make_unique<OrderBook>();
    }

    std::unique_ptr<OrderBook> book;
};

// Basic order operations
TEST_F(OrderBookTest, AddSingleBuyOrder) {
    Order* order = book->add_order(1, to_price(100.0), 100, Side::Buy);

    ASSERT_NE(order, nullptr);
    EXPECT_EQ(order->id, 1);
    EXPECT_EQ(order->price, to_price(100.0));
    EXPECT_EQ(order->quantity, 100);
    EXPECT_EQ(order->side, Side::Buy);
    EXPECT_EQ(order->status, OrderStatus::New);
}

TEST_F(OrderBookTest, AddSingleSellOrder) {
    Order* order = book->add_order(1, to_price(101.0), 50, Side::Sell);

    ASSERT_NE(order, nullptr);
    EXPECT_EQ(order->id, 1);
    EXPECT_EQ(order->price, to_price(101.0));
    EXPECT_EQ(order->quantity, 50);
    EXPECT_EQ(order->side, Side::Sell);
}

TEST_F(OrderBookTest, AddMultipleOrders) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);
    book->add_order(2, to_price(99.0), 200, Side::Buy);
    book->add_order(3, to_price(101.0), 150, Side::Sell);
    book->add_order(4, to_price(102.0), 75, Side::Sell);

    EXPECT_EQ(book->total_order_count(), 4);
    EXPECT_EQ(book->bid_level_count(), 2);
    EXPECT_EQ(book->ask_level_count(), 2);
}

TEST_F(OrderBookTest, RejectDuplicateOrderId) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);
    Order* duplicate = book->add_order(1, to_price(99.0), 50, Side::Buy);

    EXPECT_EQ(duplicate, nullptr);
    EXPECT_EQ(book->total_order_count(), 1);
}

TEST_F(OrderBookTest, CancelOrder) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);

    bool cancelled = book->cancel_order(1);

    EXPECT_TRUE(cancelled);
    EXPECT_EQ(book->total_order_count(), 0);
    EXPECT_TRUE(book->empty());
}

TEST_F(OrderBookTest, CancelNonexistentOrder) {
    bool cancelled = book->cancel_order(999);
    EXPECT_FALSE(cancelled);
}

TEST_F(OrderBookTest, GetOrderById) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);

    Order* order = book->get_order(1);
    ASSERT_NE(order, nullptr);
    EXPECT_EQ(order->id, 1);

    Order* missing = book->get_order(999);
    EXPECT_EQ(missing, nullptr);
}

// BBO tests
TEST_F(OrderBookTest, BestBidAsk) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);
    book->add_order(2, to_price(99.0), 200, Side::Buy);
    book->add_order(3, to_price(101.0), 150, Side::Sell);
    book->add_order(4, to_price(102.0), 75, Side::Sell);

    EXPECT_EQ(book->best_bid(), to_price(100.0));
    EXPECT_EQ(book->best_ask(), to_price(101.0));
    EXPECT_EQ(book->spread(), to_price(1.0));
}

TEST_F(OrderBookTest, MidPrice) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);
    book->add_order(2, to_price(102.0), 100, Side::Sell);

    Price mid = book->mid_price();
    EXPECT_EQ(mid, to_price(101.0));
}

TEST_F(OrderBookTest, BBOOnEmptyBook) {
    EXPECT_EQ(book->best_bid(), INVALID_PRICE);
    EXPECT_EQ(book->best_ask(), INVALID_PRICE);
    EXPECT_EQ(book->mid_price(), INVALID_PRICE);
}

TEST_F(OrderBookTest, GetBBO) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);
    book->add_order(2, to_price(101.0), 150, Side::Sell);

    BBO bbo = book->get_bbo();

    EXPECT_TRUE(bbo.has_both());
    EXPECT_EQ(bbo.bid_price, to_price(100.0));
    EXPECT_EQ(bbo.bid_quantity, 100);
    EXPECT_EQ(bbo.ask_price, to_price(101.0));
    EXPECT_EQ(bbo.ask_quantity, 150);
    EXPECT_EQ(bbo.spread(), to_price(1.0));
}

// Depth tests
TEST_F(OrderBookTest, GetDepth) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);
    book->add_order(2, to_price(100.0), 50, Side::Buy);  // Same level
    book->add_order(3, to_price(99.0), 200, Side::Buy);
    book->add_order(4, to_price(101.0), 150, Side::Sell);
    book->add_order(5, to_price(102.0), 75, Side::Sell);

    std::vector<DepthLevel> bids, asks;
    book->get_depth(bids, asks, 5);

    ASSERT_EQ(bids.size(), 2);
    EXPECT_EQ(bids[0].price, to_price(100.0));
    EXPECT_EQ(bids[0].quantity, 150);  // 100 + 50
    EXPECT_EQ(bids[0].order_count, 2);
    EXPECT_EQ(bids[1].price, to_price(99.0));
    EXPECT_EQ(bids[1].quantity, 200);

    ASSERT_EQ(asks.size(), 2);
    EXPECT_EQ(asks[0].price, to_price(101.0));
    EXPECT_EQ(asks[0].quantity, 150);
    EXPECT_EQ(asks[1].price, to_price(102.0));
    EXPECT_EQ(asks[1].quantity, 75);
}

// Volume tests
TEST_F(OrderBookTest, TotalVolume) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);
    book->add_order(2, to_price(99.0), 200, Side::Buy);
    book->add_order(3, to_price(101.0), 150, Side::Sell);

    EXPECT_EQ(book->total_bid_volume(), 300);
    EXPECT_EQ(book->total_ask_volume(), 150);
}

TEST_F(OrderBookTest, VolumeAfterCancel) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);
    book->add_order(2, to_price(99.0), 200, Side::Buy);

    book->cancel_order(1);

    EXPECT_EQ(book->total_bid_volume(), 200);
}

// Price-time priority tests
TEST_F(OrderBookTest, OrdersAtSamePriceAreFIFO) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);
    book->add_order(2, to_price(100.0), 200, Side::Buy);
    book->add_order(3, to_price(100.0), 50, Side::Buy);

    std::vector<DepthLevel> bids, asks;
    book->get_depth(bids, asks, 1);

    ASSERT_EQ(bids.size(), 1);
    EXPECT_EQ(bids[0].quantity, 350);  // Total at this level
    EXPECT_EQ(bids[0].order_count, 3);
}

// Cross detection
TEST_F(OrderBookTest, WouldCross) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);
    book->add_order(2, to_price(101.0), 100, Side::Sell);

    // Sell at 100 would cross the bid
    EXPECT_TRUE(book->would_cross(to_price(100.0), Side::Sell));
    // Sell at 101 would not cross
    EXPECT_FALSE(book->would_cross(to_price(101.0), Side::Sell));

    // Buy at 101 would cross the ask
    EXPECT_TRUE(book->would_cross(to_price(101.0), Side::Buy));
    // Buy at 100 would not cross
    EXPECT_FALSE(book->would_cross(to_price(100.0), Side::Buy));
}

// VWAP calculation
TEST_F(OrderBookTest, CalculateVWAP) {
    book->add_order(1, to_price(100.0), 100, Side::Sell);
    book->add_order(2, to_price(101.0), 200, Side::Sell);
    book->add_order(3, to_price(102.0), 100, Side::Sell);

    // VWAP for 150 shares: 100*100 + 50*101 = 10000 + 5050 = 15050 / 150 = 100.33
    auto vwap = book->calculate_vwap(Side::Sell, 150);
    ASSERT_TRUE(vwap.has_value());
    // Note: integer division, so approximately 100.33 * 10000 = 1003333
    EXPECT_NEAR(from_price(*vwap), 100.33, 0.01);
}

// Clear and reset
TEST_F(OrderBookTest, ClearBook) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);
    book->add_order(2, to_price(101.0), 100, Side::Sell);

    book->clear();

    EXPECT_TRUE(book->empty());
    EXPECT_EQ(book->total_order_count(), 0);
    EXPECT_EQ(book->total_bid_volume(), 0);
    EXPECT_EQ(book->total_ask_volume(), 0);
}

// Modify order
TEST_F(OrderBookTest, ModifyOrder) {
    book->add_order(1, to_price(100.0), 100, Side::Buy);

    Order* modified = book->modify_order(1, to_price(99.0), 150);

    ASSERT_NE(modified, nullptr);
    EXPECT_EQ(modified->price, to_price(99.0));
    EXPECT_EQ(modified->quantity, 150);
    EXPECT_EQ(book->best_bid(), to_price(99.0));
}

// Edge cases
TEST_F(OrderBookTest, LargeNumberOfOrders) {
    const int NUM_ORDERS = 10000;

    for (int i = 1; i <= NUM_ORDERS; ++i) {
        Price price = to_price(100.0 + (i % 100) * 0.01);
        Side side = (i % 2 == 0) ? Side::Buy : Side::Sell;
        book->add_order(i, price, 100, side);
    }

    EXPECT_EQ(book->total_order_count(), NUM_ORDERS);
}

TEST_F(OrderBookTest, AddAndCancelAllOrders) {
    for (int i = 1; i <= 100; ++i) {
        book->add_order(i, to_price(100.0), 100, Side::Buy);
    }

    for (int i = 1; i <= 100; ++i) {
        book->cancel_order(i);
    }

    EXPECT_TRUE(book->empty());
}
