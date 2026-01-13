#pragma once

#include "atlas/core/types.hpp"
#include "atlas/core/order_book.hpp"
#include "atlas/feed/market_data.hpp"
#include "atlas/feed/ring_buffer.hpp"

#include <atomic>
#include <functional>
#include <memory>
#include <thread>
#include <unordered_map>

namespace atlas {

// Callback types for feed events
using L2Callback = std::function<void(const L2Update&)>;
using L3Callback = std::function<void(const L3Update&)>;
using TradeTickCallback = std::function<void(const TradeMessage&)>;
using GapCallback = std::function<void(uint64_t expected, uint64_t received)>;

// Feed handler configuration
struct FeedHandlerConfig {
    size_t ring_buffer_capacity{65536};
    bool detect_gaps{true};
    bool process_trades{true};
    bool maintain_order_book{true};
    uint32_t max_symbols{1000};
};

// Feed statistics
struct FeedStats {
    uint64_t messages_received{0};
    uint64_t messages_processed{0};
    uint64_t sequence_gaps{0};
    uint64_t parse_errors{0};
    uint64_t buffer_overflows{0};
    uint64_t last_sequence{0};
    Timestamp last_message_time{0};
    Timestamp last_process_time{0};
};

// Feed handler for processing market data
class FeedHandler {
public:
    explicit FeedHandler(FeedHandlerConfig config = {});
    ~FeedHandler();

    // Non-copyable
    FeedHandler(const FeedHandler&) = delete;
    FeedHandler& operator=(const FeedHandler&) = delete;

    // Start/stop processing
    void start();
    void stop();
    [[nodiscard]] bool is_running() const noexcept;

    // Enqueue raw message for processing (called by network thread)
    bool enqueue_message(const void* data, size_t length);

    // Enqueue typed L2 message
    bool enqueue_l2(const L2Message& msg);

    // Process messages (call from processing thread if not using internal thread)
    size_t process_messages(size_t max_messages = 0);

    // Set callbacks
    void set_l2_callback(L2Callback callback);
    void set_l3_callback(L3Callback callback);
    void set_trade_callback(TradeTickCallback callback);
    void set_gap_callback(GapCallback callback);

    // Access order books
    [[nodiscard]] OrderBook* get_order_book(SymbolId symbol_id);
    [[nodiscard]] const OrderBook* get_order_book(SymbolId symbol_id) const;

    // Create order book for a symbol
    OrderBook& create_order_book(SymbolId symbol_id);

    // Statistics
    [[nodiscard]] const FeedStats& get_stats() const noexcept;
    void reset_stats();

private:
    // Process a single L2 message
    void process_l2_message(const L2Message& msg);

    // Apply update to order book
    void apply_to_order_book(SymbolId symbol_id, const L2Update& update);

    // Check for sequence gaps
    void check_sequence(uint64_t sequence);

    FeedHandlerConfig config_;
    FeedStats stats_;

    // Ring buffer for incoming messages
    SPSCRingBuffer<L2Message, 65536> message_queue_;

    // Order books by symbol
    std::unordered_map<SymbolId, std::unique_ptr<OrderBook>> order_books_;

    // Callbacks
    L2Callback l2_callback_;
    L3Callback l3_callback_;
    TradeTickCallback trade_callback_;
    GapCallback gap_callback_;

    // Threading
    std::atomic<bool> running_{false};
    std::thread processing_thread_;

    // Sequence tracking
    uint64_t expected_sequence_{1};
};

}  // namespace atlas
