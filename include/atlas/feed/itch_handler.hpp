#pragma once

#include "atlas/feed/itch_parser.hpp"
#include "atlas/core/order_book.hpp"
#include "atlas/core/types.hpp"

#include <string>
#include <unordered_map>
#include <functional>

namespace atlas {

// Handles ITCH messages and maintains order book state
// This is the bridge between raw ITCH feed and the order book
class ITCHHandler {
public:
    // Trade callback for execution notifications
    struct TradeInfo {
        uint64_t match_number;
        std::string symbol;
        Price price;
        Quantity quantity;
        Side side;
        uint64_t timestamp_ns;
    };

    using TradeCallback = std::function<void(const TradeInfo&)>;

    ITCHHandler() = default;

    // Set the symbol to track (empty = track all symbols)
    void set_symbol_filter(const std::string& symbol) {
        symbol_filter_ = symbol;
    }

    // Set trade callback
    void on_trade(TradeCallback cb) {
        trade_cb_ = std::move(cb);
    }

    // Get the order book for a symbol
    OrderBook* get_order_book(const std::string& symbol) {
        auto it = order_books_.find(symbol);
        if (it != order_books_.end()) {
            return &it->second;
        }
        return nullptr;
    }

    // Get or create order book for a symbol
    OrderBook& get_or_create_book(const std::string& symbol) {
        return order_books_[symbol];
    }

    // Process raw ITCH data
    size_t process(const uint8_t* data, size_t len) {
        return parser_.parse_messages(data, len);
    }

    // Initialize parser callbacks - call this after setting up your callbacks
    void initialize() {
        setup_parser_callbacks();
    }

    // Statistics
    uint64_t messages_processed() const { return parser_.messages_parsed(); }
    uint64_t orders_added() const { return orders_added_; }
    uint64_t orders_cancelled() const { return orders_cancelled_; }
    uint64_t orders_executed() const { return orders_executed_; }
    uint64_t trades_reported() const { return trades_reported_; }

    // Access underlying parser for custom callbacks
    itch::Parser& parser() { return parser_; }
    const itch::Parser& parser() const { return parser_; }

private:
    void setup_parser_callbacks() {
        // Add Order (no MPID)
        parser_.on_add_order([this](const itch::AddOrder& msg) {
            std::string symbol(msg.stock.data(), 8);
            // Trim trailing spaces
            size_t end = symbol.find_last_not_of(' ');
            if (end != std::string::npos) symbol.resize(end + 1);

            if (!symbol_filter_.empty() && symbol != symbol_filter_) {
                return;
            }

            auto& book = order_books_[symbol];
            Side side = (msg.side == itch::Side::Buy) ? Side::Buy : Side::Sell;

            // Store order info for later execution/cancel
            OrderInfo info;
            info.symbol = symbol;
            info.price = msg.price;  // Keep as fixed-point
            info.remaining_shares = msg.shares;
            info.side = side;
            info.timestamp_ns = msg.header.timestamp_ns;
            order_map_[msg.order_ref] = info;

            book.add_order(msg.order_ref, msg.price, msg.shares, side);
            ++orders_added_;
        });

        // Add Order with MPID
        parser_.on_add_order_mpid([this](const itch::AddOrderMPID& msg) {
            std::string symbol(msg.stock.data(), 8);
            size_t end = symbol.find_last_not_of(' ');
            if (end != std::string::npos) symbol.resize(end + 1);

            if (!symbol_filter_.empty() && symbol != symbol_filter_) {
                return;
            }

            auto& book = order_books_[symbol];
            Side side = (msg.side == itch::Side::Buy) ? Side::Buy : Side::Sell;

            OrderInfo info;
            info.symbol = symbol;
            info.price = msg.price;
            info.remaining_shares = msg.shares;
            info.side = side;
            info.timestamp_ns = msg.header.timestamp_ns;
            order_map_[msg.order_ref] = info;

            book.add_order(msg.order_ref, msg.price, msg.shares, side);
            ++orders_added_;
        });

        // Order Executed
        parser_.on_order_executed([this](const itch::OrderExecuted& msg) {
            auto it = order_map_.find(msg.order_ref);
            if (it == order_map_.end()) return;

            // Copy info before potential erase
            OrderInfo info = it->second;
            if (!symbol_filter_.empty() && info.symbol != symbol_filter_) {
                return;
            }

            auto* book = get_order_book(info.symbol);
            if (!book) return;

            // Reduce quantity in book
            if (msg.executed_shares >= info.remaining_shares) {
                book->cancel_order(msg.order_ref);
                order_map_.erase(it);
            } else {
                it->second.remaining_shares -= msg.executed_shares;
                // Note: OrderBook doesn't support partial cancel, so we remove and re-add
                book->cancel_order(msg.order_ref);
                book->add_order(msg.order_ref, info.price, it->second.remaining_shares, info.side);
            }

            ++orders_executed_;

            // Report trade
            if (trade_cb_) {
                TradeInfo trade;
                trade.match_number = msg.match_number;
                trade.symbol = info.symbol;
                trade.price = info.price;
                trade.quantity = msg.executed_shares;
                trade.side = info.side;
                trade.timestamp_ns = msg.header.timestamp_ns;
                trade_cb_(trade);
            }
            ++trades_reported_;
        });

        // Order Executed with Price
        parser_.on_order_executed_price([this](const itch::OrderExecutedPrice& msg) {
            auto it = order_map_.find(msg.order_ref);
            if (it == order_map_.end()) return;

            // Copy info before potential erase
            OrderInfo info = it->second;
            if (!symbol_filter_.empty() && info.symbol != symbol_filter_) {
                return;
            }

            auto* book = get_order_book(info.symbol);
            if (!book) return;

            if (msg.executed_shares >= info.remaining_shares) {
                book->cancel_order(msg.order_ref);
                order_map_.erase(it);
            } else {
                it->second.remaining_shares -= msg.executed_shares;
                book->cancel_order(msg.order_ref);
                book->add_order(msg.order_ref, info.price, it->second.remaining_shares, info.side);
            }

            ++orders_executed_;

            if (trade_cb_) {
                TradeInfo trade;
                trade.match_number = msg.match_number;
                trade.symbol = info.symbol;
                trade.price = msg.execution_price;  // Use execution price
                trade.quantity = msg.executed_shares;
                trade.side = info.side;
                trade.timestamp_ns = msg.header.timestamp_ns;
                trade_cb_(trade);
            }
            ++trades_reported_;
        });

        // Order Cancel (partial)
        parser_.on_order_cancel([this](const itch::OrderCancel& msg) {
            auto it = order_map_.find(msg.order_ref);
            if (it == order_map_.end()) return;

            auto& info = it->second;
            if (!symbol_filter_.empty() && info.symbol != symbol_filter_) {
                return;
            }

            auto* book = get_order_book(info.symbol);
            if (!book) return;

            if (msg.cancelled_shares >= info.remaining_shares) {
                book->cancel_order(msg.order_ref);
                order_map_.erase(it);
            } else {
                info.remaining_shares -= msg.cancelled_shares;
                book->cancel_order(msg.order_ref);
                book->add_order(msg.order_ref, info.price, info.remaining_shares, info.side);
            }

            ++orders_cancelled_;
        });

        // Order Delete (full cancel)
        parser_.on_order_delete([this](const itch::OrderDelete& msg) {
            auto it = order_map_.find(msg.order_ref);
            if (it == order_map_.end()) return;

            auto& info = it->second;
            if (!symbol_filter_.empty() && info.symbol != symbol_filter_) {
                return;
            }

            auto* book = get_order_book(info.symbol);
            if (book) {
                book->cancel_order(msg.order_ref);
            }

            order_map_.erase(it);
            ++orders_cancelled_;
        });

        // Order Replace
        parser_.on_order_replace([this](const itch::OrderReplace& msg) {
            auto it = order_map_.find(msg.original_order_ref);
            if (it == order_map_.end()) return;

            auto info = it->second;  // Copy
            if (!symbol_filter_.empty() && info.symbol != symbol_filter_) {
                return;
            }

            auto* book = get_order_book(info.symbol);
            if (!book) return;

            // Cancel original
            book->cancel_order(msg.original_order_ref);
            order_map_.erase(it);

            // Add new
            info.price = msg.price;
            info.remaining_shares = msg.shares;
            order_map_[msg.new_order_ref] = info;

            book->add_order(msg.new_order_ref, msg.price, msg.shares, info.side);
            ++orders_cancelled_;
            ++orders_added_;
        });

        // Trade message (non-cross, hidden order execution)
        parser_.on_trade([this](const itch::Trade& msg) {
            std::string symbol(msg.stock.data(), 8);
            size_t end = symbol.find_last_not_of(' ');
            if (end != std::string::npos) symbol.resize(end + 1);

            if (!symbol_filter_.empty() && symbol != symbol_filter_) {
                return;
            }

            if (trade_cb_) {
                TradeInfo trade;
                trade.match_number = msg.match_number;
                trade.symbol = symbol;
                trade.price = msg.price;
                trade.quantity = msg.shares;
                trade.side = (msg.side == itch::Side::Buy) ? Side::Buy : Side::Sell;
                trade.timestamp_ns = msg.header.timestamp_ns;
                trade_cb_(trade);
            }
            ++trades_reported_;
        });
    }

    // Order tracking
    struct OrderInfo {
        std::string symbol;
        Price price;
        Quantity remaining_shares;
        Side side;
        uint64_t timestamp_ns;
    };

    itch::Parser parser_;
    std::string symbol_filter_;
    std::unordered_map<std::string, OrderBook> order_books_;
    std::unordered_map<uint64_t, OrderInfo> order_map_;
    TradeCallback trade_cb_;

    // Statistics
    uint64_t orders_added_ = 0;
    uint64_t orders_cancelled_ = 0;
    uint64_t orders_executed_ = 0;
    uint64_t trades_reported_ = 0;
};

}  // namespace atlas
