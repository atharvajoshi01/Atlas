#pragma once

#include "atlas/core/types.hpp"
#include "atlas/core/order.hpp"
#include "atlas/core/order_book.hpp"

#include <functional>
#include <vector>
#include <deque>

namespace atlas {

// Matching engine configuration
struct MatchingEngineConfig {
    bool self_trade_prevention{true};   // Prevent orders from same participant matching
    bool allow_market_orders{true};     // Allow market orders
    bool allow_ioc_orders{true};        // Allow Immediate-or-Cancel
    bool allow_fok_orders{true};        // Allow Fill-or-Kill
    Quantity max_order_quantity{1000000};  // Maximum order size
};

// Matching engine for a single symbol
// Handles order submission, matching, and execution
class MatchingEngine {
public:
    explicit MatchingEngine(MatchingEngineConfig config = {});
    ~MatchingEngine() = default;

    // Non-copyable
    MatchingEngine(const MatchingEngine&) = delete;
    MatchingEngine& operator=(const MatchingEngine&) = delete;

    // Movable
    MatchingEngine(MatchingEngine&&) noexcept = default;
    MatchingEngine& operator=(MatchingEngine&&) noexcept = default;

    // Submit a new order - main entry point
    // Returns execution result with fill information
    ExecutionResult submit_order(OrderId id, Price price, Quantity quantity,
                                  Side side, OrderType type = OrderType::Limit,
                                  Timestamp timestamp = 0,
                                  uint64_t participant_id = 0);

    // Submit a market order (convenience method)
    ExecutionResult submit_market_order(OrderId id, Quantity quantity, Side side,
                                         Timestamp timestamp = 0,
                                         uint64_t participant_id = 0);

    // Cancel an existing order
    bool cancel_order(OrderId id);

    // Modify an existing order (cancel + replace)
    ExecutionResult modify_order(OrderId id, Price new_price, Quantity new_quantity);

    // Access the underlying order book
    [[nodiscard]] const OrderBook& get_order_book() const noexcept;
    [[nodiscard]] OrderBook& get_order_book() noexcept;

    // Get trades generated since last call (and clear the queue)
    std::vector<Trade> get_trades();

    // Get all trades (without clearing)
    [[nodiscard]] const std::deque<Trade>& peek_trades() const noexcept;

    // Set trade callback (called immediately when trade occurs)
    void set_trade_callback(TradeCallback callback);

    // Statistics
    [[nodiscard]] uint64_t total_trades() const noexcept;
    [[nodiscard]] uint64_t total_volume() const noexcept;
    [[nodiscard]] uint64_t total_orders_submitted() const noexcept;
    [[nodiscard]] uint64_t total_orders_cancelled() const noexcept;

    // Reset engine state
    void reset();

private:
    // Match an incoming order against the book
    // Returns the number of trades executed
    size_t match_order(Order* order, uint64_t participant_id);

    // Try to match against a specific side of the book
    template <typename BookSide>
    size_t match_against_side(Order* order, BookSide& book_side,
                              uint64_t participant_id);

    // Execute a single match between two orders
    void execute_match(Order* aggressive, Order* passive, Quantity match_qty);

    // Check if orders can match (self-trade prevention)
    [[nodiscard]] bool can_match(const Order* aggressive, const Order* passive,
                                  uint64_t aggressive_participant,
                                  uint64_t passive_participant) const noexcept;

    // Validate order before processing
    [[nodiscard]] bool validate_order(OrderId id, Price price, Quantity quantity,
                                       Side side, OrderType type) const;

    OrderBook book_;
    MatchingEngineConfig config_;

    // Trade queue for batched retrieval
    std::deque<Trade> trade_queue_;
    TradeCallback trade_callback_;

    // Statistics
    uint64_t total_trades_{0};
    uint64_t total_volume_{0};
    uint64_t total_orders_submitted_{0};
    uint64_t total_orders_cancelled_{0};
    uint64_t next_trade_id_{1};
};

}  // namespace atlas
