#pragma once

#include "atlas/core/types.hpp"
#include "atlas/memory/pool_allocator.hpp"

#include <cstdint>

namespace atlas {

// Forward declaration
class PriceLevel;

// Order structure optimized for cache efficiency
// Aligned to cache line boundary to prevent false sharing
// Uses intrusive list pointers for O(1) removal from price level
struct alignas(CACHE_LINE_SIZE) Order {
    // Core order data - frequently accessed together
    OrderId id{INVALID_ORDER_ID};
    Price price{INVALID_PRICE};
    Quantity quantity{0};
    Quantity filled_quantity{0};
    Timestamp timestamp{0};

    // Order metadata
    Side side{Side::Buy};
    OrderType type{OrderType::Limit};
    OrderStatus status{OrderStatus::New};
    SymbolId symbol_id{0};

    // Intrusive doubly-linked list pointers for O(1) removal
    Order* prev{nullptr};
    Order* next{nullptr};

    // Pointer to parent price level for quick access
    PriceLevel* level{nullptr};

    // Constructors
    Order() = default;

    Order(OrderId id_, Price price_, Quantity quantity_, Side side_,
          OrderType type_ = OrderType::Limit, Timestamp ts = 0)
        : id(id_)
        , price(price_)
        , quantity(quantity_)
        , filled_quantity(0)
        , timestamp(ts)
        , side(side_)
        , type(type_)
        , status(OrderStatus::New)
        , symbol_id(0)
        , prev(nullptr)
        , next(nullptr)
        , level(nullptr) {}

    // Remaining quantity to fill
    [[nodiscard]] Quantity remaining() const noexcept {
        return quantity - filled_quantity;
    }

    // Check if order is completely filled
    [[nodiscard]] bool is_filled() const noexcept {
        return filled_quantity >= quantity;
    }

    // Check if order is active (can be matched or cancelled)
    [[nodiscard]] bool is_active() const noexcept {
        return status == OrderStatus::New ||
               status == OrderStatus::PartiallyFilled;
    }

    // Check if order is a buy order
    [[nodiscard]] bool is_buy() const noexcept {
        return side == Side::Buy;
    }

    // Check if order is a sell order
    [[nodiscard]] bool is_sell() const noexcept {
        return side == Side::Sell;
    }

    // Fill the order by the given quantity
    // Returns the actual quantity filled (may be less if order is partially filled)
    Quantity fill(Quantity fill_qty) noexcept {
        Quantity actual_fill = std::min(fill_qty, remaining());
        filled_quantity += actual_fill;

        if (is_filled()) {
            status = OrderStatus::Filled;
        } else if (filled_quantity > 0) {
            status = OrderStatus::PartiallyFilled;
        }

        return actual_fill;
    }

    // Cancel the order
    void cancel() noexcept {
        status = OrderStatus::Cancelled;
    }

    // Reset order for reuse from pool
    void reset() noexcept {
        id = INVALID_ORDER_ID;
        price = INVALID_PRICE;
        quantity = 0;
        filled_quantity = 0;
        timestamp = 0;
        side = Side::Buy;
        type = OrderType::Limit;
        status = OrderStatus::New;
        symbol_id = 0;
        prev = nullptr;
        next = nullptr;
        level = nullptr;
    }
};

// Ensure Order fits nicely in cache
static_assert(sizeof(Order) <= 2 * CACHE_LINE_SIZE,
              "Order should fit in at most 2 cache lines");
static_assert(alignof(Order) == CACHE_LINE_SIZE,
              "Order must be cache-line aligned");

// Trade event generated when orders match
struct Trade {
    uint64_t trade_id;
    OrderId buyer_order_id;
    OrderId seller_order_id;
    Price price;
    Quantity quantity;
    Timestamp timestamp;
    Side aggressor_side;  // Side of the incoming (aggressive) order
};

// Execution result for an order submission
struct ExecutionResult {
    OrderId order_id;
    OrderStatus status;
    Quantity filled_quantity;
    Price avg_fill_price;  // VWAP of fills, fixed-point
    uint32_t trade_count;  // Number of trades generated

    [[nodiscard]] bool is_accepted() const noexcept {
        return status != OrderStatus::Rejected;
    }

    [[nodiscard]] bool is_filled() const noexcept {
        return status == OrderStatus::Filled;
    }
};

// Book update event
struct BookUpdate {
    Price price;
    Quantity quantity;  // New total quantity at price (0 = level removed)
    Side side;
    Timestamp timestamp;
};

}  // namespace atlas
