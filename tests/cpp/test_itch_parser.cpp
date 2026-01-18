#include <gtest/gtest.h>
#include "atlas/feed/itch_parser.hpp"
#include "atlas/feed/itch_handler.hpp"

#include <cstring>
#include <vector>

using namespace atlas;
using namespace atlas::itch;

// Helper to create big-endian bytes
class ITCHMessageBuilder {
public:
    ITCHMessageBuilder& add_byte(uint8_t b) {
        data_.push_back(b);
        return *this;
    }

    ITCHMessageBuilder& add_be16(uint16_t val) {
        data_.push_back(static_cast<uint8_t>(val >> 8));
        data_.push_back(static_cast<uint8_t>(val));
        return *this;
    }

    ITCHMessageBuilder& add_be32(uint32_t val) {
        data_.push_back(static_cast<uint8_t>(val >> 24));
        data_.push_back(static_cast<uint8_t>(val >> 16));
        data_.push_back(static_cast<uint8_t>(val >> 8));
        data_.push_back(static_cast<uint8_t>(val));
        return *this;
    }

    ITCHMessageBuilder& add_be48(uint64_t val) {
        data_.push_back(static_cast<uint8_t>(val >> 40));
        data_.push_back(static_cast<uint8_t>(val >> 32));
        data_.push_back(static_cast<uint8_t>(val >> 24));
        data_.push_back(static_cast<uint8_t>(val >> 16));
        data_.push_back(static_cast<uint8_t>(val >> 8));
        data_.push_back(static_cast<uint8_t>(val));
        return *this;
    }

    ITCHMessageBuilder& add_be64(uint64_t val) {
        data_.push_back(static_cast<uint8_t>(val >> 56));
        data_.push_back(static_cast<uint8_t>(val >> 48));
        data_.push_back(static_cast<uint8_t>(val >> 40));
        data_.push_back(static_cast<uint8_t>(val >> 32));
        data_.push_back(static_cast<uint8_t>(val >> 24));
        data_.push_back(static_cast<uint8_t>(val >> 16));
        data_.push_back(static_cast<uint8_t>(val >> 8));
        data_.push_back(static_cast<uint8_t>(val));
        return *this;
    }

    ITCHMessageBuilder& add_string(const std::string& s, size_t len) {
        for (size_t i = 0; i < len; ++i) {
            if (i < s.size()) {
                data_.push_back(static_cast<uint8_t>(s[i]));
            } else {
                data_.push_back(' ');  // Pad with spaces
            }
        }
        return *this;
    }

    const uint8_t* data() const { return data_.data(); }
    size_t size() const { return data_.size(); }
    void clear() { data_.clear(); }

private:
    std::vector<uint8_t> data_;
};

// ============================================================================
// Endianness Tests
// ============================================================================

TEST(ITCHEndianness, Be16ToHost) {
    uint8_t data[] = {0x12, 0x34};
    EXPECT_EQ(be16_to_host(data), 0x1234);
}

TEST(ITCHEndianness, Be32ToHost) {
    uint8_t data[] = {0x12, 0x34, 0x56, 0x78};
    EXPECT_EQ(be32_to_host(data), 0x12345678u);
}

TEST(ITCHEndianness, Be48ToHost) {
    uint8_t data[] = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05};
    EXPECT_EQ(be48_to_host(data), 0x000102030405ull);
}

TEST(ITCHEndianness, Be64ToHost) {
    uint8_t data[] = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08};
    EXPECT_EQ(be64_to_host(data), 0x0102030405060708ull);
}

// ============================================================================
// Message Length Tests
// ============================================================================

TEST(ITCHMessageLength, KnownTypes) {
    EXPECT_EQ(Parser::message_length(MessageType::SystemEvent), 12u);
    EXPECT_EQ(Parser::message_length(MessageType::StockDirectory), 39u);
    EXPECT_EQ(Parser::message_length(MessageType::AddOrder), 36u);
    EXPECT_EQ(Parser::message_length(MessageType::AddOrderMPID), 40u);
    EXPECT_EQ(Parser::message_length(MessageType::OrderExecuted), 31u);
    EXPECT_EQ(Parser::message_length(MessageType::OrderExecutedPrice), 36u);
    EXPECT_EQ(Parser::message_length(MessageType::OrderCancel), 23u);
    EXPECT_EQ(Parser::message_length(MessageType::OrderDelete), 19u);
    EXPECT_EQ(Parser::message_length(MessageType::OrderReplace), 35u);
    EXPECT_EQ(Parser::message_length(MessageType::Trade), 44u);
}

TEST(ITCHMessageLength, UnknownType) {
    EXPECT_EQ(Parser::message_length(MessageType::Unknown), 0u);
}

// ============================================================================
// System Event Parsing
// ============================================================================

TEST(ITCHParser, SystemEvent) {
    ITCHMessageBuilder builder;
    builder.add_byte('S')        // Message type
           .add_be16(1)          // Stock locate
           .add_be16(0)          // Tracking number
           .add_be48(123456789)  // Timestamp
           .add_byte('O');       // Event code (Start of Messages)

    Parser parser;
    bool callback_called = false;

    parser.on_system_event([&](const SystemEvent& msg) {
        callback_called = true;
        EXPECT_EQ(msg.header.type, MessageType::SystemEvent);
        EXPECT_EQ(msg.header.stock_locate, 1);
        EXPECT_EQ(msg.header.timestamp_ns, 123456789ull);
        EXPECT_EQ(msg.event_code, 'O');
    });

    size_t consumed = parser.parse_message(builder.data(), builder.size());
    EXPECT_EQ(consumed, 12u);
    EXPECT_TRUE(callback_called);
}

// ============================================================================
// Add Order Parsing
// ============================================================================

TEST(ITCHParser, AddOrder) {
    ITCHMessageBuilder builder;
    builder.add_byte('A')           // Message type
           .add_be16(42)            // Stock locate
           .add_be16(1)             // Tracking number
           .add_be48(1000000000)    // Timestamp (1 second)
           .add_be64(12345678)      // Order reference number
           .add_byte('B')           // Side (Buy)
           .add_be32(100)           // Shares
           .add_string("AAPL", 8)   // Stock symbol
           .add_be32(1500000);      // Price (150.0000)

    Parser parser;
    bool callback_called = false;

    parser.on_add_order([&](const AddOrder& msg) {
        callback_called = true;
        EXPECT_EQ(msg.header.type, MessageType::AddOrder);
        EXPECT_EQ(msg.header.stock_locate, 42);
        EXPECT_EQ(msg.header.timestamp_ns, 1000000000ull);
        EXPECT_EQ(msg.order_ref, 12345678ull);
        EXPECT_EQ(msg.side, itch::Side::Buy);
        EXPECT_EQ(msg.shares, 100u);
        EXPECT_EQ(std::string(msg.stock.data(), 4), "AAPL");
        EXPECT_EQ(msg.price, 1500000u);
        EXPECT_DOUBLE_EQ(msg.price_double(), 150.0);
    });

    size_t consumed = parser.parse_message(builder.data(), builder.size());
    EXPECT_EQ(consumed, 36u);
    EXPECT_TRUE(callback_called);
}

TEST(ITCHParser, AddOrderSell) {
    ITCHMessageBuilder builder;
    builder.add_byte('A')
           .add_be16(1)
           .add_be16(0)
           .add_be48(0)
           .add_be64(999)
           .add_byte('S')           // Side (Sell)
           .add_be32(50)
           .add_string("MSFT", 8)
           .add_be32(3500000);      // Price (350.0000)

    Parser parser;
    itch::Side received_side = itch::Side::Buy;

    parser.on_add_order([&](const AddOrder& msg) {
        received_side = msg.side;
    });

    parser.parse_message(builder.data(), builder.size());
    EXPECT_EQ(received_side, itch::Side::Sell);
}

// ============================================================================
// Order Delete Parsing
// ============================================================================

TEST(ITCHParser, OrderDelete) {
    ITCHMessageBuilder builder;
    builder.add_byte('D')
           .add_be16(42)
           .add_be16(0)
           .add_be48(2000000000)
           .add_be64(12345678);     // Order to delete

    Parser parser;
    uint64_t deleted_order = 0;

    parser.on_order_delete([&](const OrderDelete& msg) {
        deleted_order = msg.order_ref;
    });

    size_t consumed = parser.parse_message(builder.data(), builder.size());
    EXPECT_EQ(consumed, 19u);
    EXPECT_EQ(deleted_order, 12345678ull);
}

// ============================================================================
// Order Cancel Parsing
// ============================================================================

TEST(ITCHParser, OrderCancel) {
    ITCHMessageBuilder builder;
    builder.add_byte('X')
           .add_be16(1)
           .add_be16(0)
           .add_be48(3000000000)
           .add_be64(11111111)
           .add_be32(25);           // Cancel 25 shares

    Parser parser;
    uint32_t cancelled_shares = 0;

    parser.on_order_cancel([&](const OrderCancel& msg) {
        cancelled_shares = msg.cancelled_shares;
    });

    size_t consumed = parser.parse_message(builder.data(), builder.size());
    EXPECT_EQ(consumed, 23u);
    EXPECT_EQ(cancelled_shares, 25u);
}

// ============================================================================
// Order Replace Parsing
// ============================================================================

TEST(ITCHParser, OrderReplace) {
    ITCHMessageBuilder builder;
    builder.add_byte('U')
           .add_be16(1)
           .add_be16(0)
           .add_be48(4000000000)
           .add_be64(11111111)      // Original order
           .add_be64(22222222)      // New order
           .add_be32(200)           // New shares
           .add_be32(1510000);      // New price (151.0000)

    Parser parser;
    bool callback_called = false;

    parser.on_order_replace([&](const OrderReplace& msg) {
        callback_called = true;
        EXPECT_EQ(msg.original_order_ref, 11111111ull);
        EXPECT_EQ(msg.new_order_ref, 22222222ull);
        EXPECT_EQ(msg.shares, 200u);
        EXPECT_EQ(msg.price, 1510000u);
    });

    size_t consumed = parser.parse_message(builder.data(), builder.size());
    EXPECT_EQ(consumed, 35u);
    EXPECT_TRUE(callback_called);
}

// ============================================================================
// Order Executed Parsing
// ============================================================================

TEST(ITCHParser, OrderExecuted) {
    ITCHMessageBuilder builder;
    builder.add_byte('E')
           .add_be16(1)
           .add_be16(0)
           .add_be48(5000000000)
           .add_be64(12345678)      // Order ref
           .add_be32(50)            // Executed shares
           .add_be64(999888777);    // Match number

    Parser parser;
    bool callback_called = false;

    parser.on_order_executed([&](const OrderExecuted& msg) {
        callback_called = true;
        EXPECT_EQ(msg.order_ref, 12345678ull);
        EXPECT_EQ(msg.executed_shares, 50u);
        EXPECT_EQ(msg.match_number, 999888777ull);
    });

    size_t consumed = parser.parse_message(builder.data(), builder.size());
    EXPECT_EQ(consumed, 31u);
    EXPECT_TRUE(callback_called);
}

// ============================================================================
// Trade Parsing
// ============================================================================

TEST(ITCHParser, Trade) {
    ITCHMessageBuilder builder;
    builder.add_byte('P')
           .add_be16(1)
           .add_be16(0)
           .add_be48(6000000000)
           .add_be64(0)             // Order ref (0 for hidden)
           .add_byte('B')           // Side
           .add_be32(100)           // Shares
           .add_string("GOOGL", 8)  // Stock
           .add_be32(1400000)       // Price (140.0000)
           .add_be64(123123123);    // Match number

    Parser parser;
    bool callback_called = false;

    parser.on_trade([&](const itch::Trade& msg) {
        callback_called = true;
        EXPECT_EQ(msg.shares, 100u);
        EXPECT_EQ(std::string(msg.stock.data(), 5), "GOOGL");
        EXPECT_DOUBLE_EQ(msg.price_double(), 140.0);
    });

    size_t consumed = parser.parse_message(builder.data(), builder.size());
    EXPECT_EQ(consumed, 44u);
    EXPECT_TRUE(callback_called);
}

// ============================================================================
// Multiple Messages Parsing
// ============================================================================

TEST(ITCHParser, MultipleMessages) {
    ITCHMessageBuilder builder;

    // Add Order
    builder.add_byte('A')
           .add_be16(1).add_be16(0).add_be48(1000000)
           .add_be64(1).add_byte('B').add_be32(100)
           .add_string("AAPL", 8).add_be32(1500000);

    // Order Delete
    builder.add_byte('D')
           .add_be16(1).add_be16(0).add_be48(2000000)
           .add_be64(1);

    Parser parser;
    int add_count = 0;
    int delete_count = 0;

    parser.on_add_order([&](const AddOrder&) { ++add_count; });
    parser.on_order_delete([&](const OrderDelete&) { ++delete_count; });

    size_t consumed = parser.parse_messages(builder.data(), builder.size());

    EXPECT_EQ(consumed, 36u + 19u);  // AddOrder + OrderDelete
    EXPECT_EQ(add_count, 1);
    EXPECT_EQ(delete_count, 1);
    EXPECT_EQ(parser.messages_parsed(), 2u);
}

// ============================================================================
// Statistics Tests
// ============================================================================

TEST(ITCHParser, Statistics) {
    ITCHMessageBuilder builder;
    builder.add_byte('D')
           .add_be16(1).add_be16(0).add_be48(0)
           .add_be64(1);

    Parser parser;
    parser.on_order_delete([](const OrderDelete&) {});

    EXPECT_EQ(parser.messages_parsed(), 0u);
    EXPECT_EQ(parser.bytes_parsed(), 0u);

    parser.parse_message(builder.data(), builder.size());

    EXPECT_EQ(parser.messages_parsed(), 1u);
    EXPECT_EQ(parser.bytes_parsed(), 19u);

    parser.reset_stats();

    EXPECT_EQ(parser.messages_parsed(), 0u);
    EXPECT_EQ(parser.bytes_parsed(), 0u);
}

// ============================================================================
// Error Handling Tests
// ============================================================================

TEST(ITCHParser, InsufficientData) {
    uint8_t partial_data[] = {'A', 0x00, 0x01};  // Only 3 bytes of AddOrder

    Parser parser;
    parser.on_add_order([](const AddOrder&) { FAIL() << "Should not be called"; });

    size_t consumed = parser.parse_message(partial_data, sizeof(partial_data));
    EXPECT_EQ(consumed, 0u);  // Should return 0 for insufficient data
}

TEST(ITCHParser, UnknownMessageType) {
    uint8_t unknown_data[] = {'Z', 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};

    Parser parser;
    size_t consumed = parser.parse_message(unknown_data, sizeof(unknown_data));
    EXPECT_EQ(consumed, 0u);  // Unknown message type
}

TEST(ITCHParser, EmptyBuffer) {
    Parser parser;
    size_t consumed = parser.parse_message(nullptr, 0);
    EXPECT_EQ(consumed, 0u);
}

// ============================================================================
// ITCH Handler Integration Tests
// ============================================================================

TEST(ITCHHandler, BasicOrderFlow) {
    ITCHHandler handler;
    handler.set_symbol_filter("AAPL");
    handler.initialize();

    // Build Add Order message
    ITCHMessageBuilder builder;
    builder.add_byte('A')
           .add_be16(1).add_be16(0).add_be48(1000000)
           .add_be64(12345)
           .add_byte('B')
           .add_be32(100)
           .add_string("AAPL", 8)
           .add_be32(1500000);  // $150.00

    handler.process(builder.data(), builder.size());

    EXPECT_EQ(handler.orders_added(), 1u);

    auto* book = handler.get_order_book("AAPL");
    ASSERT_NE(book, nullptr);
    EXPECT_EQ(book->bid_level_count(), 1u);
}

TEST(ITCHHandler, AddAndDelete) {
    ITCHHandler handler;
    handler.initialize();

    // Add Order
    ITCHMessageBuilder add_msg;
    add_msg.add_byte('A')
           .add_be16(1).add_be16(0).add_be48(1000000)
           .add_be64(100)
           .add_byte('B')
           .add_be32(50)
           .add_string("MSFT", 8)
           .add_be32(3500000);

    handler.process(add_msg.data(), add_msg.size());

    // Delete Order
    ITCHMessageBuilder del_msg;
    del_msg.add_byte('D')
           .add_be16(1).add_be16(0).add_be48(2000000)
           .add_be64(100);

    handler.process(del_msg.data(), del_msg.size());

    EXPECT_EQ(handler.orders_added(), 1u);
    EXPECT_EQ(handler.orders_cancelled(), 1u);

    auto* book = handler.get_order_book("MSFT");
    ASSERT_NE(book, nullptr);
    EXPECT_EQ(book->bid_level_count(), 0u);
}

TEST(ITCHHandler, TradeCallback) {
    ITCHHandler handler;
    handler.initialize();

    int trades_received = 0;
    handler.on_trade([&](const ITCHHandler::TradeInfo& trade) {
        ++trades_received;
        EXPECT_EQ(trade.symbol, "NVDA");
        EXPECT_EQ(trade.quantity, 200u);
    });

    // Add Order first
    ITCHMessageBuilder add_msg;
    add_msg.add_byte('A')
           .add_be16(1).add_be16(0).add_be48(1000000)
           .add_be64(555)
           .add_byte('S')
           .add_be32(200)
           .add_string("NVDA", 8)
           .add_be32(5000000);

    handler.process(add_msg.data(), add_msg.size());

    // Execute order
    ITCHMessageBuilder exec_msg;
    exec_msg.add_byte('E')
            .add_be16(1).add_be16(0).add_be48(2000000)
            .add_be64(555)
            .add_be32(200)
            .add_be64(777777);

    handler.process(exec_msg.data(), exec_msg.size());

    EXPECT_EQ(trades_received, 1);
    EXPECT_EQ(handler.trades_reported(), 1u);
}

TEST(ITCHHandler, SymbolFilter) {
    ITCHHandler handler;
    handler.set_symbol_filter("AAPL");
    handler.initialize();

    // Add AAPL order (should be tracked)
    ITCHMessageBuilder aapl_msg;
    aapl_msg.add_byte('A')
            .add_be16(1).add_be16(0).add_be48(1000000)
            .add_be64(1)
            .add_byte('B')
            .add_be32(100)
            .add_string("AAPL", 8)
            .add_be32(1500000);

    // Add MSFT order (should be ignored)
    ITCHMessageBuilder msft_msg;
    msft_msg.add_byte('A')
            .add_be16(2).add_be16(0).add_be48(1000000)
            .add_be64(2)
            .add_byte('B')
            .add_be32(100)
            .add_string("MSFT", 8)
            .add_be32(3500000);

    handler.process(aapl_msg.data(), aapl_msg.size());
    handler.process(msft_msg.data(), msft_msg.size());

    // Only AAPL should be counted
    EXPECT_EQ(handler.orders_added(), 1u);
    EXPECT_NE(handler.get_order_book("AAPL"), nullptr);
}

TEST(ITCHHandler, MultipleSymbols) {
    ITCHHandler handler;
    // No filter - track all symbols
    handler.initialize();

    ITCHMessageBuilder aapl_msg;
    aapl_msg.add_byte('A')
            .add_be16(1).add_be16(0).add_be48(1000000)
            .add_be64(1).add_byte('B').add_be32(100)
            .add_string("AAPL", 8).add_be32(1500000);

    ITCHMessageBuilder msft_msg;
    msft_msg.add_byte('A')
            .add_be16(2).add_be16(0).add_be48(1000000)
            .add_be64(2).add_byte('S').add_be32(50)
            .add_string("MSFT", 8).add_be32(3500000);

    handler.process(aapl_msg.data(), aapl_msg.size());
    handler.process(msft_msg.data(), msft_msg.size());

    EXPECT_EQ(handler.orders_added(), 2u);
    EXPECT_NE(handler.get_order_book("AAPL"), nullptr);
    EXPECT_NE(handler.get_order_book("MSFT"), nullptr);
}
