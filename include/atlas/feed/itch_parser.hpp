#pragma once

#include <array>
#include <cstdint>
#include <cstring>
#include <functional>
#include <string>
#include <string_view>

namespace atlas::itch {

// ITCH 5.0 uses big-endian byte order
// These helpers convert to host byte order

inline uint16_t be16_to_host(const uint8_t* p) {
    return (static_cast<uint16_t>(p[0]) << 8) | p[1];
}

inline uint32_t be32_to_host(const uint8_t* p) {
    return (static_cast<uint32_t>(p[0]) << 24) |
           (static_cast<uint32_t>(p[1]) << 16) |
           (static_cast<uint32_t>(p[2]) << 8) |
           p[3];
}

inline uint64_t be48_to_host(const uint8_t* p) {
    return (static_cast<uint64_t>(p[0]) << 40) |
           (static_cast<uint64_t>(p[1]) << 32) |
           (static_cast<uint64_t>(p[2]) << 24) |
           (static_cast<uint64_t>(p[3]) << 16) |
           (static_cast<uint64_t>(p[4]) << 8) |
           p[5];
}

inline uint64_t be64_to_host(const uint8_t* p) {
    return (static_cast<uint64_t>(p[0]) << 56) |
           (static_cast<uint64_t>(p[1]) << 48) |
           (static_cast<uint64_t>(p[2]) << 40) |
           (static_cast<uint64_t>(p[3]) << 32) |
           (static_cast<uint64_t>(p[4]) << 24) |
           (static_cast<uint64_t>(p[5]) << 16) |
           (static_cast<uint64_t>(p[6]) << 8) |
           p[7];
}

// Message type identifiers
enum class MessageType : char {
    // System messages
    SystemEvent = 'S',
    StockDirectory = 'R',
    StockTradingAction = 'H',
    RegSHORestriction = 'Y',
    MarketParticipantPosition = 'L',
    MWCBDeclineLevel = 'V',
    MWCBStatus = 'W',
    IPOQuotingPeriod = 'K',
    LULDAuctionCollar = 'J',
    OperationalHalt = 'h',

    // Order messages (most important for order book)
    AddOrder = 'A',
    AddOrderMPID = 'F',
    OrderExecuted = 'E',
    OrderExecutedPrice = 'C',
    OrderCancel = 'X',
    OrderDelete = 'D',
    OrderReplace = 'U',

    // Trade messages
    Trade = 'P',
    CrossTrade = 'Q',
    BrokenTrade = 'B',

    // Auction messages
    NOII = 'I',
    RPII = 'N',

    Unknown = '?'
};

// Side indicator
enum class Side : char {
    Buy = 'B',
    Sell = 'S'
};

// Convert 8-byte stock symbol to string (removes trailing spaces)
inline std::string stock_to_string(const uint8_t* stock) {
    std::string s(reinterpret_cast<const char*>(stock), 8);
    // Trim trailing spaces
    size_t end = s.find_last_not_of(' ');
    if (end != std::string::npos) {
        s.resize(end + 1);
    }
    return s;
}

// ============================================================================
// Message Structures (parsed from binary)
// ============================================================================

// Base timestamp for all messages (nanoseconds since midnight)
struct MessageHeader {
    MessageType type;
    uint16_t stock_locate;
    uint16_t tracking_number;
    uint64_t timestamp_ns;  // 6-byte timestamp expanded to 8
};

// 'S' - System Event Message
struct SystemEvent {
    MessageHeader header;
    char event_code;  // 'O'=Start, 'S'=Start Hours, 'Q'=Start Market, 'M'=End Market, 'E'=End Hours, 'C'=End
};

// 'R' - Stock Directory Message
struct StockDirectory {
    MessageHeader header;
    std::array<char, 8> stock;
    char market_category;
    char financial_status;
    uint32_t round_lot_size;
    char round_lots_only;
    char issue_classification;
    std::array<char, 2> issue_subtype;
    char authenticity;
    char short_sale_threshold;
    char ipo_flag;
    char luld_reference_price_tier;
    char etp_flag;
    uint32_t etp_leverage_factor;
    char inverse_indicator;
};

// 'A' - Add Order (No MPID)
struct AddOrder {
    MessageHeader header;
    uint64_t order_ref;
    Side side;
    uint32_t shares;
    std::array<char, 8> stock;
    uint32_t price;  // Fixed point, 4 decimal places (divide by 10000)

    double price_double() const { return price / 10000.0; }
};

// 'F' - Add Order with MPID Attribution
struct AddOrderMPID {
    MessageHeader header;
    uint64_t order_ref;
    Side side;
    uint32_t shares;
    std::array<char, 8> stock;
    uint32_t price;
    std::array<char, 4> mpid;

    double price_double() const { return price / 10000.0; }
};

// 'E' - Order Executed
struct OrderExecuted {
    MessageHeader header;
    uint64_t order_ref;
    uint32_t executed_shares;
    uint64_t match_number;
};

// 'C' - Order Executed with Price
struct OrderExecutedPrice {
    MessageHeader header;
    uint64_t order_ref;
    uint32_t executed_shares;
    uint64_t match_number;
    char printable;
    uint32_t execution_price;

    double price_double() const { return execution_price / 10000.0; }
};

// 'X' - Order Cancel
struct OrderCancel {
    MessageHeader header;
    uint64_t order_ref;
    uint32_t cancelled_shares;
};

// 'D' - Order Delete
struct OrderDelete {
    MessageHeader header;
    uint64_t order_ref;
};

// 'U' - Order Replace
struct OrderReplace {
    MessageHeader header;
    uint64_t original_order_ref;
    uint64_t new_order_ref;
    uint32_t shares;
    uint32_t price;

    double price_double() const { return price / 10000.0; }
};

// 'P' - Trade Message (non-cross)
struct Trade {
    MessageHeader header;
    uint64_t order_ref;
    Side side;
    uint32_t shares;
    std::array<char, 8> stock;
    uint32_t price;
    uint64_t match_number;

    double price_double() const { return price / 10000.0; }
};

// 'Q' - Cross Trade
struct CrossTrade {
    MessageHeader header;
    uint64_t shares;
    std::array<char, 8> stock;
    uint32_t cross_price;
    uint64_t match_number;
    char cross_type;

    double price_double() const { return cross_price / 10000.0; }
};

// 'B' - Broken Trade
struct BrokenTrade {
    MessageHeader header;
    uint64_t match_number;
};

// 'H' - Stock Trading Action
struct StockTradingAction {
    MessageHeader header;
    std::array<char, 8> stock;
    char trading_state;  // 'H'=Halted, 'P'=Paused, 'Q'=QuotationOnly, 'T'=Trading
    char reserved;
    std::array<char, 4> reason;
};

// 'I' - NOII (Net Order Imbalance Indicator)
struct NOII {
    MessageHeader header;
    uint64_t paired_shares;
    uint64_t imbalance_shares;
    char imbalance_direction;
    std::array<char, 8> stock;
    uint32_t far_price;
    uint32_t near_price;
    uint32_t current_reference_price;
    char cross_type;
    char price_variation_indicator;
};

// ============================================================================
// Parser Class
// ============================================================================

class Parser {
public:
    // Callback types for each message
    using SystemEventCallback = std::function<void(const SystemEvent&)>;
    using StockDirectoryCallback = std::function<void(const StockDirectory&)>;
    using AddOrderCallback = std::function<void(const AddOrder&)>;
    using AddOrderMPIDCallback = std::function<void(const AddOrderMPID&)>;
    using OrderExecutedCallback = std::function<void(const OrderExecuted&)>;
    using OrderExecutedPriceCallback = std::function<void(const OrderExecutedPrice&)>;
    using OrderCancelCallback = std::function<void(const OrderCancel&)>;
    using OrderDeleteCallback = std::function<void(const OrderDelete&)>;
    using OrderReplaceCallback = std::function<void(const OrderReplace&)>;
    using TradeCallback = std::function<void(const Trade&)>;
    using CrossTradeCallback = std::function<void(const CrossTrade&)>;
    using BrokenTradeCallback = std::function<void(const BrokenTrade&)>;
    using StockTradingActionCallback = std::function<void(const StockTradingAction&)>;
    using NOIICallback = std::function<void(const NOII&)>;

    Parser() = default;

    // Set callbacks
    void on_system_event(SystemEventCallback cb) { system_event_cb_ = std::move(cb); }
    void on_stock_directory(StockDirectoryCallback cb) { stock_directory_cb_ = std::move(cb); }
    void on_add_order(AddOrderCallback cb) { add_order_cb_ = std::move(cb); }
    void on_add_order_mpid(AddOrderMPIDCallback cb) { add_order_mpid_cb_ = std::move(cb); }
    void on_order_executed(OrderExecutedCallback cb) { order_executed_cb_ = std::move(cb); }
    void on_order_executed_price(OrderExecutedPriceCallback cb) { order_executed_price_cb_ = std::move(cb); }
    void on_order_cancel(OrderCancelCallback cb) { order_cancel_cb_ = std::move(cb); }
    void on_order_delete(OrderDeleteCallback cb) { order_delete_cb_ = std::move(cb); }
    void on_order_replace(OrderReplaceCallback cb) { order_replace_cb_ = std::move(cb); }
    void on_trade(TradeCallback cb) { trade_cb_ = std::move(cb); }
    void on_cross_trade(CrossTradeCallback cb) { cross_trade_cb_ = std::move(cb); }
    void on_broken_trade(BrokenTradeCallback cb) { broken_trade_cb_ = std::move(cb); }
    void on_stock_trading_action(StockTradingActionCallback cb) { stock_trading_action_cb_ = std::move(cb); }
    void on_noii(NOIICallback cb) { noii_cb_ = std::move(cb); }

    // Parse a single message from buffer
    // Returns number of bytes consumed, or 0 if insufficient data
    size_t parse_message(const uint8_t* data, size_t len);

    // Parse multiple messages from buffer
    // Returns total bytes consumed
    size_t parse_messages(const uint8_t* data, size_t len);

    // Get message length for a given message type
    static size_t message_length(MessageType type);

    // Statistics
    uint64_t messages_parsed() const { return messages_parsed_; }
    uint64_t bytes_parsed() const { return bytes_parsed_; }
    void reset_stats() { messages_parsed_ = 0; bytes_parsed_ = 0; }

private:
    // Parse header common to all messages
    MessageHeader parse_header(const uint8_t* data);

    // Callbacks
    SystemEventCallback system_event_cb_;
    StockDirectoryCallback stock_directory_cb_;
    AddOrderCallback add_order_cb_;
    AddOrderMPIDCallback add_order_mpid_cb_;
    OrderExecutedCallback order_executed_cb_;
    OrderExecutedPriceCallback order_executed_price_cb_;
    OrderCancelCallback order_cancel_cb_;
    OrderDeleteCallback order_delete_cb_;
    OrderReplaceCallback order_replace_cb_;
    TradeCallback trade_cb_;
    CrossTradeCallback cross_trade_cb_;
    BrokenTradeCallback broken_trade_cb_;
    StockTradingActionCallback stock_trading_action_cb_;
    NOIICallback noii_cb_;

    // Statistics
    uint64_t messages_parsed_ = 0;
    uint64_t bytes_parsed_ = 0;
};

// ============================================================================
// Inline Implementation
// ============================================================================

inline MessageHeader Parser::parse_header(const uint8_t* data) {
    MessageHeader h;
    h.type = static_cast<MessageType>(data[0]);
    h.stock_locate = be16_to_host(data + 1);
    h.tracking_number = be16_to_host(data + 3);
    h.timestamp_ns = be48_to_host(data + 5);
    return h;
}

inline size_t Parser::message_length(MessageType type) {
    switch (type) {
        case MessageType::SystemEvent:           return 12;
        case MessageType::StockDirectory:        return 39;
        case MessageType::StockTradingAction:    return 25;
        case MessageType::RegSHORestriction:     return 20;
        case MessageType::MarketParticipantPosition: return 26;
        case MessageType::MWCBDeclineLevel:      return 35;
        case MessageType::MWCBStatus:            return 12;
        case MessageType::IPOQuotingPeriod:      return 28;
        case MessageType::LULDAuctionCollar:     return 35;
        case MessageType::OperationalHalt:       return 21;
        case MessageType::AddOrder:              return 36;
        case MessageType::AddOrderMPID:          return 40;
        case MessageType::OrderExecuted:         return 31;
        case MessageType::OrderExecutedPrice:    return 36;
        case MessageType::OrderCancel:           return 23;
        case MessageType::OrderDelete:           return 19;
        case MessageType::OrderReplace:          return 35;
        case MessageType::Trade:                 return 44;
        case MessageType::CrossTrade:            return 40;
        case MessageType::BrokenTrade:           return 19;
        case MessageType::NOII:                  return 50;
        case MessageType::RPII:                  return 20;
        default:                                 return 0;
    }
}

inline size_t Parser::parse_message(const uint8_t* data, size_t len) {
    if (len < 1) return 0;

    MessageType type = static_cast<MessageType>(data[0]);
    size_t msg_len = message_length(type);

    if (msg_len == 0 || len < msg_len) {
        return 0;  // Unknown message type or insufficient data
    }

    switch (type) {
        case MessageType::SystemEvent: {
            if (system_event_cb_) {
                SystemEvent msg;
                msg.header = parse_header(data);
                msg.event_code = static_cast<char>(data[11]);
                system_event_cb_(msg);
            }
            break;
        }

        case MessageType::StockDirectory: {
            if (stock_directory_cb_) {
                StockDirectory msg;
                msg.header = parse_header(data);
                std::memcpy(msg.stock.data(), data + 11, 8);
                msg.market_category = static_cast<char>(data[19]);
                msg.financial_status = static_cast<char>(data[20]);
                msg.round_lot_size = be32_to_host(data + 21);
                msg.round_lots_only = static_cast<char>(data[25]);
                msg.issue_classification = static_cast<char>(data[26]);
                std::memcpy(msg.issue_subtype.data(), data + 27, 2);
                msg.authenticity = static_cast<char>(data[29]);
                msg.short_sale_threshold = static_cast<char>(data[30]);
                msg.ipo_flag = static_cast<char>(data[31]);
                msg.luld_reference_price_tier = static_cast<char>(data[32]);
                msg.etp_flag = static_cast<char>(data[33]);
                msg.etp_leverage_factor = be32_to_host(data + 34);
                msg.inverse_indicator = static_cast<char>(data[38]);
                stock_directory_cb_(msg);
            }
            break;
        }

        case MessageType::AddOrder: {
            if (add_order_cb_) {
                AddOrder msg;
                msg.header = parse_header(data);
                msg.order_ref = be64_to_host(data + 11);
                msg.side = static_cast<Side>(data[19]);
                msg.shares = be32_to_host(data + 20);
                std::memcpy(msg.stock.data(), data + 24, 8);
                msg.price = be32_to_host(data + 32);
                add_order_cb_(msg);
            }
            break;
        }

        case MessageType::AddOrderMPID: {
            if (add_order_mpid_cb_) {
                AddOrderMPID msg;
                msg.header = parse_header(data);
                msg.order_ref = be64_to_host(data + 11);
                msg.side = static_cast<Side>(data[19]);
                msg.shares = be32_to_host(data + 20);
                std::memcpy(msg.stock.data(), data + 24, 8);
                msg.price = be32_to_host(data + 32);
                std::memcpy(msg.mpid.data(), data + 36, 4);
                add_order_mpid_cb_(msg);
            }
            break;
        }

        case MessageType::OrderExecuted: {
            if (order_executed_cb_) {
                OrderExecuted msg;
                msg.header = parse_header(data);
                msg.order_ref = be64_to_host(data + 11);
                msg.executed_shares = be32_to_host(data + 19);
                msg.match_number = be64_to_host(data + 23);
                order_executed_cb_(msg);
            }
            break;
        }

        case MessageType::OrderExecutedPrice: {
            if (order_executed_price_cb_) {
                OrderExecutedPrice msg;
                msg.header = parse_header(data);
                msg.order_ref = be64_to_host(data + 11);
                msg.executed_shares = be32_to_host(data + 19);
                msg.match_number = be64_to_host(data + 23);
                msg.printable = static_cast<char>(data[31]);
                msg.execution_price = be32_to_host(data + 32);
                order_executed_price_cb_(msg);
            }
            break;
        }

        case MessageType::OrderCancel: {
            if (order_cancel_cb_) {
                OrderCancel msg;
                msg.header = parse_header(data);
                msg.order_ref = be64_to_host(data + 11);
                msg.cancelled_shares = be32_to_host(data + 19);
                order_cancel_cb_(msg);
            }
            break;
        }

        case MessageType::OrderDelete: {
            if (order_delete_cb_) {
                OrderDelete msg;
                msg.header = parse_header(data);
                msg.order_ref = be64_to_host(data + 11);
                order_delete_cb_(msg);
            }
            break;
        }

        case MessageType::OrderReplace: {
            if (order_replace_cb_) {
                OrderReplace msg;
                msg.header = parse_header(data);
                msg.original_order_ref = be64_to_host(data + 11);
                msg.new_order_ref = be64_to_host(data + 19);
                msg.shares = be32_to_host(data + 27);
                msg.price = be32_to_host(data + 31);
                order_replace_cb_(msg);
            }
            break;
        }

        case MessageType::Trade: {
            if (trade_cb_) {
                Trade msg;
                msg.header = parse_header(data);
                msg.order_ref = be64_to_host(data + 11);
                msg.side = static_cast<Side>(data[19]);
                msg.shares = be32_to_host(data + 20);
                std::memcpy(msg.stock.data(), data + 24, 8);
                msg.price = be32_to_host(data + 32);
                msg.match_number = be64_to_host(data + 36);
                trade_cb_(msg);
            }
            break;
        }

        case MessageType::CrossTrade: {
            if (cross_trade_cb_) {
                CrossTrade msg;
                msg.header = parse_header(data);
                msg.shares = be64_to_host(data + 11);
                std::memcpy(msg.stock.data(), data + 19, 8);
                msg.cross_price = be32_to_host(data + 27);
                msg.match_number = be64_to_host(data + 31);
                msg.cross_type = static_cast<char>(data[39]);
                cross_trade_cb_(msg);
            }
            break;
        }

        case MessageType::BrokenTrade: {
            if (broken_trade_cb_) {
                BrokenTrade msg;
                msg.header = parse_header(data);
                msg.match_number = be64_to_host(data + 11);
                broken_trade_cb_(msg);
            }
            break;
        }

        case MessageType::StockTradingAction: {
            if (stock_trading_action_cb_) {
                StockTradingAction msg;
                msg.header = parse_header(data);
                std::memcpy(msg.stock.data(), data + 11, 8);
                msg.trading_state = static_cast<char>(data[19]);
                msg.reserved = static_cast<char>(data[20]);
                std::memcpy(msg.reason.data(), data + 21, 4);
                stock_trading_action_cb_(msg);
            }
            break;
        }

        case MessageType::NOII: {
            if (noii_cb_) {
                NOII msg;
                msg.header = parse_header(data);
                msg.paired_shares = be64_to_host(data + 11);
                msg.imbalance_shares = be64_to_host(data + 19);
                msg.imbalance_direction = static_cast<char>(data[27]);
                std::memcpy(msg.stock.data(), data + 28, 8);
                msg.far_price = be32_to_host(data + 36);
                msg.near_price = be32_to_host(data + 40);
                msg.current_reference_price = be32_to_host(data + 44);
                msg.cross_type = static_cast<char>(data[48]);
                msg.price_variation_indicator = static_cast<char>(data[49]);
                noii_cb_(msg);
            }
            break;
        }

        default:
            // Skip unknown message types
            break;
    }

    ++messages_parsed_;
    bytes_parsed_ += msg_len;
    return msg_len;
}

inline size_t Parser::parse_messages(const uint8_t* data, size_t len) {
    size_t total_consumed = 0;

    while (total_consumed < len) {
        size_t consumed = parse_message(data + total_consumed, len - total_consumed);
        if (consumed == 0) {
            break;  // Insufficient data or unknown message
        }
        total_consumed += consumed;
    }

    return total_consumed;
}

}  // namespace atlas::itch
