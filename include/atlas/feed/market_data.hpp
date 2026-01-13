#pragma once

#include "atlas/core/types.hpp"
#include "atlas/memory/pool_allocator.hpp"

#include <array>
#include <cstdint>
#include <cstring>

namespace atlas {

// Message types for market data
enum class MessageType : uint8_t {
    AddOrder = 'A',
    DeleteOrder = 'D',
    ModifyOrder = 'U',
    ExecutedOrder = 'E',
    Trade = 'P',
    SystemEvent = 'S',
    BookSnapshot = 'B',
    Heartbeat = 'H'
};

// Action type for order updates
enum class OrderAction : uint8_t {
    Add = 0,
    Modify = 1,
    Delete = 2,
    Execute = 3
};

// Market data message header
struct alignas(8) MarketDataHeader {
    MessageType msg_type;
    uint8_t padding[3];
    uint32_t msg_length;
    uint64_t sequence_num;
    uint64_t send_time;      // Nanoseconds since midnight
    uint64_t receive_time;   // Local receive time
};

static_assert(sizeof(MarketDataHeader) == 32, "Header should be 32 bytes");

// Add order message
struct alignas(CACHE_LINE_SIZE) AddOrderMessage {
    MarketDataHeader header;
    OrderId order_id;
    SymbolId symbol_id;
    Price price;
    Quantity quantity;
    Side side;
    uint8_t padding[7];

    AddOrderMessage() {
        std::memset(this, 0, sizeof(*this));
        header.msg_type = MessageType::AddOrder;
        header.msg_length = sizeof(*this);
    }
};

// Delete order message
struct alignas(CACHE_LINE_SIZE) DeleteOrderMessage {
    MarketDataHeader header;
    OrderId order_id;
    SymbolId symbol_id;
    uint8_t padding[4];

    DeleteOrderMessage() {
        std::memset(this, 0, sizeof(*this));
        header.msg_type = MessageType::DeleteOrder;
        header.msg_length = sizeof(*this);
    }
};

// Modify order message
struct alignas(CACHE_LINE_SIZE) ModifyOrderMessage {
    MarketDataHeader header;
    OrderId order_id;
    SymbolId symbol_id;
    Price new_price;
    Quantity new_quantity;

    ModifyOrderMessage() {
        std::memset(this, 0, sizeof(*this));
        header.msg_type = MessageType::ModifyOrder;
        header.msg_length = sizeof(*this);
    }
};

// Executed order message
struct alignas(CACHE_LINE_SIZE) ExecutedOrderMessage {
    MarketDataHeader header;
    OrderId order_id;
    SymbolId symbol_id;
    Quantity executed_quantity;
    Price execution_price;
    uint64_t match_id;

    ExecutedOrderMessage() {
        std::memset(this, 0, sizeof(*this));
        header.msg_type = MessageType::ExecutedOrder;
        header.msg_length = sizeof(*this);
    }
};

// Trade message (anonymous trade)
struct alignas(CACHE_LINE_SIZE) TradeMessage {
    MarketDataHeader header;
    SymbolId symbol_id;
    Price price;
    Quantity quantity;
    Side aggressor_side;
    uint8_t padding[3];
    uint64_t trade_id;

    TradeMessage() {
        std::memset(this, 0, sizeof(*this));
        header.msg_type = MessageType::Trade;
        header.msg_length = sizeof(*this);
    }
};

// L2 (price level) update message
struct L2Update {
    SymbolId symbol_id;
    Price price;
    Quantity quantity;
    Side side;
    OrderAction action;
    uint8_t level;  // Level from BBO (0 = best, 1 = second best, etc.)
    uint8_t padding;
    Timestamp timestamp;
};

// L3 (order level) update message
struct L3Update {
    SymbolId symbol_id;
    OrderId order_id;
    Price price;
    Quantity quantity;
    Side side;
    OrderAction action;
    uint16_t padding;
    Timestamp timestamp;
};

// Book snapshot level
struct SnapshotLevel {
    Price price;
    Quantity quantity;
    uint32_t order_count;
    uint32_t padding;
};

// Book snapshot message (for initial state)
struct BookSnapshotMessage {
    MarketDataHeader header;
    SymbolId symbol_id;
    uint32_t bid_levels;
    uint32_t ask_levels;
    // Followed by bid_levels + ask_levels SnapshotLevel entries

    [[nodiscard]] size_t total_size() const noexcept {
        return sizeof(*this) + (bid_levels + ask_levels) * sizeof(SnapshotLevel);
    }
};

// Union for generic message handling
union MarketDataMessage {
    MarketDataHeader header;
    AddOrderMessage add;
    DeleteOrderMessage del;
    ModifyOrderMessage modify;
    ExecutedOrderMessage executed;
    TradeMessage trade;
    BookSnapshotMessage snapshot;

    [[nodiscard]] MessageType type() const noexcept {
        return header.msg_type;
    }

    [[nodiscard]] uint32_t length() const noexcept {
        return header.msg_length;
    }

    [[nodiscard]] uint64_t sequence() const noexcept {
        return header.sequence_num;
    }
};

// Simplified L2 message for ring buffer (fixed size for efficiency)
struct alignas(CACHE_LINE_SIZE) L2Message {
    Timestamp timestamp;
    SymbolId symbol_id;
    Price price;
    Quantity quantity;
    Side side;
    OrderAction action;
    uint16_t padding;
    uint64_t sequence;
};

static_assert(sizeof(L2Message) <= CACHE_LINE_SIZE,
              "L2Message should fit in one cache line");

}  // namespace atlas
