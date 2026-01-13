#include "atlas/feed/feed_handler.hpp"

#include <chrono>

namespace atlas {

FeedHandler::FeedHandler(FeedHandlerConfig config)
    : config_(std::move(config)) {}

FeedHandler::~FeedHandler() {
    stop();
}

void FeedHandler::start() {
    if (running_.exchange(true)) {
        return;  // Already running
    }

    processing_thread_ = std::thread([this]() {
        while (running_.load(std::memory_order_relaxed)) {
            size_t processed = process_messages(1000);
            if (processed == 0) {
                // No messages, yield to avoid busy spinning
                std::this_thread::yield();
            }
        }
    });
}

void FeedHandler::stop() {
    running_.store(false, std::memory_order_relaxed);
    if (processing_thread_.joinable()) {
        processing_thread_.join();
    }
}

bool FeedHandler::is_running() const noexcept {
    return running_.load(std::memory_order_relaxed);
}

bool FeedHandler::enqueue_message(const void* data, size_t length) {
    // Parse the header to determine message type
    if (length < sizeof(MarketDataHeader)) [[unlikely]] {
        ++stats_.parse_errors;
        return false;
    }

    const auto* header = static_cast<const MarketDataHeader*>(data);

    // For now, we only handle L2 updates directly
    // Other message types would be parsed and converted here
    ++stats_.messages_received;
    return true;
}

bool FeedHandler::enqueue_l2(const L2Message& msg) {
    if (!message_queue_.try_push(msg)) [[unlikely]] {
        ++stats_.buffer_overflows;
        return false;
    }
    ++stats_.messages_received;
    return true;
}

size_t FeedHandler::process_messages(size_t max_messages) {
    size_t processed = 0;
    L2Message msg;

    while ((max_messages == 0 || processed < max_messages) &&
           message_queue_.try_pop(msg)) {
        process_l2_message(msg);
        ++processed;
    }

    stats_.messages_processed += processed;
    return processed;
}

void FeedHandler::process_l2_message(const L2Message& msg) {
    // Check for sequence gaps
    if (config_.detect_gaps) {
        check_sequence(msg.sequence);
    }

    stats_.last_sequence = msg.sequence;
    stats_.last_message_time = msg.timestamp;

    // Create L2Update for callback and order book
    L2Update update{};
    update.symbol_id = msg.symbol_id;
    update.price = msg.price;
    update.quantity = msg.quantity;
    update.side = msg.side;
    update.action = msg.action;
    update.timestamp = msg.timestamp;

    // Call L2 callback
    if (l2_callback_) {
        l2_callback_(update);
    }

    // Apply to order book
    if (config_.maintain_order_book) {
        apply_to_order_book(msg.symbol_id, update);
    }

    stats_.last_process_time = static_cast<Timestamp>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()
        ).count()
    );
}

void FeedHandler::apply_to_order_book(SymbolId symbol_id, const L2Update& update) {
    OrderBook* book = get_order_book(symbol_id);
    if (!book) {
        // Auto-create order book if configured
        if (order_books_.size() < config_.max_symbols) {
            book = &create_order_book(symbol_id);
        } else {
            return;
        }
    }

    // L2 updates modify aggregate levels, not individual orders
    // This is a simplified implementation - real L2 books track levels differently
    static OrderId next_synthetic_id = 1;

    switch (update.action) {
        case OrderAction::Add:
        case OrderAction::Modify:
            // For L2, we treat this as setting the level quantity
            // In practice, we'd need to track individual orders or level state
            if (update.quantity > 0) {
                book->add_order(
                    next_synthetic_id++,
                    update.price,
                    update.quantity,
                    update.side,
                    OrderType::Limit,
                    update.timestamp
                );
            }
            break;

        case OrderAction::Delete:
            // Remove orders at this price level
            // This is simplified - would need level tracking in practice
            break;

        case OrderAction::Execute:
            // Trade occurred at this level
            break;
    }
}

void FeedHandler::check_sequence(uint64_t sequence) {
    if (expected_sequence_ != 0 && sequence != expected_sequence_) {
        ++stats_.sequence_gaps;
        if (gap_callback_) {
            gap_callback_(expected_sequence_, sequence);
        }
    }
    expected_sequence_ = sequence + 1;
}

void FeedHandler::set_l2_callback(L2Callback callback) {
    l2_callback_ = std::move(callback);
}

void FeedHandler::set_l3_callback(L3Callback callback) {
    l3_callback_ = std::move(callback);
}

void FeedHandler::set_trade_callback(TradeTickCallback callback) {
    trade_callback_ = std::move(callback);
}

void FeedHandler::set_gap_callback(GapCallback callback) {
    gap_callback_ = std::move(callback);
}

OrderBook* FeedHandler::get_order_book(SymbolId symbol_id) {
    auto it = order_books_.find(symbol_id);
    return it != order_books_.end() ? it->second.get() : nullptr;
}

const OrderBook* FeedHandler::get_order_book(SymbolId symbol_id) const {
    auto it = order_books_.find(symbol_id);
    return it != order_books_.end() ? it->second.get() : nullptr;
}

OrderBook& FeedHandler::create_order_book(SymbolId symbol_id) {
    auto [it, inserted] = order_books_.try_emplace(
        symbol_id,
        std::make_unique<OrderBook>()
    );
    return *it->second;
}

const FeedStats& FeedHandler::get_stats() const noexcept {
    return stats_;
}

void FeedHandler::reset_stats() {
    stats_ = FeedStats{};
}

}  // namespace atlas
