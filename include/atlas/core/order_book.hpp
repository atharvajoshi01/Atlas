#pragma once

#include "atlas/core/types.hpp"
#include "atlas/core/order.hpp"
#include "atlas/core/price_level.hpp"
#include "atlas/memory/pool_allocator.hpp"

#include <functional>
#include <map>
#include <unordered_map>
#include <vector>
#include <optional>

namespace atlas {

// Callback types
using TradeCallback = std::function<void(const Trade&)>;
using BookUpdateCallback = std::function<void(const BookUpdate&)>;

// BBO (Best Bid and Offer) snapshot
struct BBO {
    Price bid_price{INVALID_PRICE};
    Quantity bid_quantity{0};
    Price ask_price{INVALID_PRICE};
    Quantity ask_quantity{0};

    [[nodiscard]] bool has_bid() const noexcept {
        return bid_price != INVALID_PRICE;
    }

    [[nodiscard]] bool has_ask() const noexcept {
        return ask_price != INVALID_PRICE;
    }

    [[nodiscard]] bool has_both() const noexcept {
        return has_bid() && has_ask();
    }

    [[nodiscard]] Price spread() const noexcept {
        if (!has_both()) return INVALID_PRICE;
        return ask_price - bid_price;
    }

    [[nodiscard]] Price mid_price() const noexcept {
        if (!has_both()) return INVALID_PRICE;
        return (bid_price + ask_price) / 2;
    }
};

// Depth level for market data
struct DepthLevel {
    Price price;
    Quantity quantity;
    size_t order_count;
};

// Order book for a single symbol
// Maintains bid and ask price levels with price-time priority
class OrderBook {
public:
    // Default order pool capacity
    static constexpr size_t DEFAULT_ORDER_POOL_SIZE = 100000;

    explicit OrderBook(size_t pool_size = DEFAULT_ORDER_POOL_SIZE);
    ~OrderBook();

    // Non-copyable
    OrderBook(const OrderBook&) = delete;
    OrderBook& operator=(const OrderBook&) = delete;

    // Movable
    OrderBook(OrderBook&&) noexcept;
    OrderBook& operator=(OrderBook&&) noexcept;

    // Core operations - these are the hot path
    // Add a new order to the book
    // Returns pointer to the order (owned by the book) or nullptr on failure
    [[nodiscard]] Order* add_order(OrderId id, Price price, Quantity quantity,
                                   Side side, OrderType type = OrderType::Limit,
                                   Timestamp timestamp = 0);

    // Cancel an existing order by ID
    // Returns true if order was found and cancelled
    bool cancel_order(OrderId id);

    // Modify an existing order (cancel and replace)
    // Returns pointer to new order or nullptr on failure
    [[nodiscard]] Order* modify_order(OrderId id, Price new_price,
                                       Quantity new_quantity);

    // Get order by ID
    [[nodiscard]] Order* get_order(OrderId id) const;

    // BBO queries - extremely fast
    [[nodiscard]] BBO get_bbo() const noexcept;
    [[nodiscard]] Price best_bid() const noexcept;
    [[nodiscard]] Price best_ask() const noexcept;
    [[nodiscard]] Quantity best_bid_quantity() const noexcept;
    [[nodiscard]] Quantity best_ask_quantity() const noexcept;
    [[nodiscard]] Price mid_price() const noexcept;
    [[nodiscard]] Price spread() const noexcept;

    // Market depth queries
    void get_bid_depth(std::vector<DepthLevel>& levels, size_t max_levels) const;
    void get_ask_depth(std::vector<DepthLevel>& levels, size_t max_levels) const;
    void get_depth(std::vector<DepthLevel>& bids,
                   std::vector<DepthLevel>& asks,
                   size_t max_levels) const;

    // Volume queries
    [[nodiscard]] Quantity total_bid_volume() const noexcept;
    [[nodiscard]] Quantity total_ask_volume() const noexcept;
    [[nodiscard]] size_t bid_level_count() const noexcept;
    [[nodiscard]] size_t ask_level_count() const noexcept;
    [[nodiscard]] size_t total_order_count() const noexcept;

    // VWAP for walking the book
    [[nodiscard]] std::optional<Price> calculate_vwap(Side side,
                                                       Quantity target_qty) const;

    // Check if order would cross the book
    [[nodiscard]] bool would_cross(Price price, Side side) const noexcept;

    // Callbacks
    void set_trade_callback(TradeCallback callback);
    void set_book_update_callback(BookUpdateCallback callback);

    // Clear all orders
    void clear();

    // Check if book is empty
    [[nodiscard]] bool empty() const noexcept;

private:
    // Internal helper to get or create a price level
    PriceLevel& get_or_create_bid_level(Price price);
    PriceLevel& get_or_create_ask_level(Price price);

    // Remove empty price levels
    void remove_bid_level_if_empty(Price price);
    void remove_ask_level_if_empty(Price price);

    // Notify callbacks
    void notify_book_update(Price price, Quantity quantity, Side side);

    // Bid side: sorted descending by price (best bid first)
    std::map<Price, PriceLevel, std::greater<Price>> bids_;

    // Ask side: sorted ascending by price (best ask first)
    std::map<Price, PriceLevel, std::less<Price>> asks_;

    // Order index for O(1) lookup by ID
    std::unordered_map<OrderId, Order*> order_index_;

    // Memory pool for orders
    PoolAllocator<Order>* order_pool_;
    bool owns_pool_{false};

    // Cached values for fast BBO access
    mutable Price cached_best_bid_{INVALID_PRICE};
    mutable Price cached_best_ask_{INVALID_PRICE};
    mutable bool bbo_cache_valid_{false};

    // Total volumes
    Quantity total_bid_volume_{0};
    Quantity total_ask_volume_{0};

    // Callbacks
    TradeCallback trade_callback_;
    BookUpdateCallback book_update_callback_;

    // Trade ID counter
    uint64_t next_trade_id_{1};
};

}  // namespace atlas
