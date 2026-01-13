#include "atlas/matching/matching_engine.hpp"

#include <algorithm>

namespace atlas {

MatchingEngine::MatchingEngine(MatchingEngineConfig config)
    : config_(std::move(config)) {
    // Set up trade callback to also queue trades
    book_.set_trade_callback([this](const Trade& trade) {
        trade_queue_.push_back(trade);
        if (trade_callback_) {
            trade_callback_(trade);
        }
    });
}

ExecutionResult MatchingEngine::submit_order(OrderId id, Price price,
                                              Quantity quantity, Side side,
                                              OrderType type, Timestamp timestamp,
                                              uint64_t participant_id) {
    ++total_orders_submitted_;

    ExecutionResult result{};
    result.order_id = id;
    result.status = OrderStatus::Rejected;
    result.filled_quantity = 0;
    result.avg_fill_price = 0;
    result.trade_count = 0;

    // Validate order
    if (!validate_order(id, price, quantity, side, type)) [[unlikely]] {
        return result;
    }

    // Handle market orders
    if (type == OrderType::Market) {
        if (!config_.allow_market_orders) [[unlikely]] {
            return result;
        }
        // Set price to cross the entire book
        price = (side == Side::Buy) ? std::numeric_limits<Price>::max()
                                     : std::numeric_limits<Price>::min();
    }

    // For FOK orders, check if we can fill the entire quantity
    if (type == OrderType::FOK) {
        if (!config_.allow_fok_orders) [[unlikely]] {
            return result;
        }

        Quantity available = 0;
        if (side == Side::Buy) {
            // Check ask side
            for (const auto& [ask_price, level] :
                 static_cast<const std::map<Price, PriceLevel>&>(
                     reinterpret_cast<const std::map<Price, PriceLevel>&>(book_))) {
                // This is a hack - we need proper access to the book's internal structure
                break;  // Will implement properly with order book access
            }
        }
        // For now, we'll check during matching
    }

    // Create temporary order for matching
    Order temp_order(id, price, quantity, side, type, timestamp);

    // Try to match against the book
    Quantity original_qty = quantity;
    int64_t total_cost = 0;
    size_t trade_count = 0;

    // Match against opposite side
    if (side == Side::Buy) {
        // Match against asks (lowest first)
        while (temp_order.remaining() > 0) {
            Price best_ask = book_.best_ask();
            if (best_ask == INVALID_PRICE || best_ask > price) {
                break;  // No more matching prices
            }

            // Get the best ask level's front order
            // We need to access orders through the book
            // For now, we'll use the book's VWAP to estimate fills
            auto vwap = book_.calculate_vwap(Side::Sell, temp_order.remaining());
            if (!vwap) break;

            // Walk the book and match
            Quantity to_fill = temp_order.remaining();
            Quantity available = book_.best_ask_quantity();
            Quantity fill_qty = std::min(to_fill, available);

            if (fill_qty > 0) {
                // Record the fill
                total_cost += static_cast<int64_t>(best_ask) *
                              static_cast<int64_t>(fill_qty);
                temp_order.fill(fill_qty);
                total_volume_ += fill_qty;
                ++trade_count;
                ++total_trades_;

                // Generate trade event
                Trade trade{};
                trade.trade_id = next_trade_id_++;
                trade.buyer_order_id = id;
                trade.seller_order_id = 0;  // Would need access to passive order
                trade.price = best_ask;
                trade.quantity = fill_qty;
                trade.timestamp = timestamp;
                trade.aggressor_side = Side::Buy;
                trade_queue_.push_back(trade);
                if (trade_callback_) {
                    trade_callback_(trade);
                }

                // Remove filled quantity from book
                // This is simplified - real implementation would update individual orders
            }

            // Move to next level if current is exhausted
            if (book_.best_ask_quantity() == 0) {
                break;  // Level exhausted, check next
            }
        }
    } else {
        // Match against bids (highest first)
        while (temp_order.remaining() > 0) {
            Price best_bid = book_.best_bid();
            if (best_bid == INVALID_PRICE || best_bid < price) {
                break;  // No more matching prices
            }

            Quantity to_fill = temp_order.remaining();
            Quantity available = book_.best_bid_quantity();
            Quantity fill_qty = std::min(to_fill, available);

            if (fill_qty > 0) {
                total_cost += static_cast<int64_t>(best_bid) *
                              static_cast<int64_t>(fill_qty);
                temp_order.fill(fill_qty);
                total_volume_ += fill_qty;
                ++trade_count;
                ++total_trades_;

                Trade trade{};
                trade.trade_id = next_trade_id_++;
                trade.buyer_order_id = 0;
                trade.seller_order_id = id;
                trade.price = best_bid;
                trade.quantity = fill_qty;
                trade.timestamp = timestamp;
                trade.aggressor_side = Side::Sell;
                trade_queue_.push_back(trade);
                if (trade_callback_) {
                    trade_callback_(trade);
                }
            }

            if (book_.best_bid_quantity() == 0) {
                break;
            }
        }
    }

    // Calculate fill results
    Quantity filled = original_qty - temp_order.remaining();
    result.filled_quantity = filled;
    result.trade_count = static_cast<uint32_t>(trade_count);

    if (filled > 0) {
        result.avg_fill_price = static_cast<Price>(total_cost /
                                static_cast<int64_t>(filled));
    }

    // Handle remaining quantity based on order type
    if (temp_order.remaining() > 0) {
        if (type == OrderType::Market || type == OrderType::IOC) {
            // Cancel remaining
            result.status = filled > 0 ? OrderStatus::PartiallyFilled
                                        : OrderStatus::Cancelled;
        } else if (type == OrderType::FOK) {
            // FOK must fill completely or not at all
            if (filled < original_qty) {
                // Rollback fills (in real implementation)
                result.status = OrderStatus::Cancelled;
                result.filled_quantity = 0;
            }
        } else {
            // Limit order - add remaining to book
            Order* book_order = book_.add_order(
                id, price, temp_order.remaining(), side, type, timestamp);

            if (book_order) {
                result.status = filled > 0 ? OrderStatus::PartiallyFilled
                                           : OrderStatus::New;
            } else {
                result.status = OrderStatus::Rejected;
            }
        }
    } else {
        result.status = OrderStatus::Filled;
    }

    return result;
}

ExecutionResult MatchingEngine::submit_market_order(OrderId id, Quantity quantity,
                                                     Side side, Timestamp timestamp,
                                                     uint64_t participant_id) {
    return submit_order(id, 0, quantity, side, OrderType::Market,
                        timestamp, participant_id);
}

bool MatchingEngine::cancel_order(OrderId id) {
    bool cancelled = book_.cancel_order(id);
    if (cancelled) {
        ++total_orders_cancelled_;
    }
    return cancelled;
}

ExecutionResult MatchingEngine::modify_order(OrderId id, Price new_price,
                                              Quantity new_quantity) {
    Order* existing = book_.get_order(id);
    if (!existing) {
        ExecutionResult result{};
        result.order_id = id;
        result.status = OrderStatus::Rejected;
        return result;
    }

    Side side = existing->side;
    OrderType type = existing->type;
    Timestamp timestamp = existing->timestamp;

    cancel_order(id);
    return submit_order(id, new_price, new_quantity, side, type, timestamp);
}

const OrderBook& MatchingEngine::get_order_book() const noexcept {
    return book_;
}

OrderBook& MatchingEngine::get_order_book() noexcept {
    return book_;
}

std::vector<Trade> MatchingEngine::get_trades() {
    std::vector<Trade> trades(trade_queue_.begin(), trade_queue_.end());
    trade_queue_.clear();
    return trades;
}

const std::deque<Trade>& MatchingEngine::peek_trades() const noexcept {
    return trade_queue_;
}

void MatchingEngine::set_trade_callback(TradeCallback callback) {
    trade_callback_ = std::move(callback);
}

uint64_t MatchingEngine::total_trades() const noexcept {
    return total_trades_;
}

uint64_t MatchingEngine::total_volume() const noexcept {
    return total_volume_;
}

uint64_t MatchingEngine::total_orders_submitted() const noexcept {
    return total_orders_submitted_;
}

uint64_t MatchingEngine::total_orders_cancelled() const noexcept {
    return total_orders_cancelled_;
}

void MatchingEngine::reset() {
    book_.clear();
    trade_queue_.clear();
    total_trades_ = 0;
    total_volume_ = 0;
    total_orders_submitted_ = 0;
    total_orders_cancelled_ = 0;
    next_trade_id_ = 1;
}

bool MatchingEngine::validate_order(OrderId id, Price price, Quantity quantity,
                                     Side side, OrderType type) const {
    // Check for invalid order ID
    if (id == INVALID_ORDER_ID) [[unlikely]] {
        return false;
    }

    // Check for zero quantity
    if (quantity == 0) [[unlikely]] {
        return false;
    }

    // Check for excessive quantity
    if (quantity > config_.max_order_quantity) [[unlikely]] {
        return false;
    }

    // Check for invalid price on limit orders
    if (type == OrderType::Limit && price <= 0) [[unlikely]] {
        return false;
    }

    // Check order type is allowed
    if (type == OrderType::IOC && !config_.allow_ioc_orders) [[unlikely]] {
        return false;
    }

    if (type == OrderType::FOK && !config_.allow_fok_orders) [[unlikely]] {
        return false;
    }

    return true;
}

bool MatchingEngine::can_match(const Order* aggressive, const Order* passive,
                                uint64_t aggressive_participant,
                                uint64_t passive_participant) const noexcept {
    // Self-trade prevention
    if (config_.self_trade_prevention &&
        aggressive_participant != 0 &&
        aggressive_participant == passive_participant) {
        return false;
    }
    return true;
}

}  // namespace atlas
