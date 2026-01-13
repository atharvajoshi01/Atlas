#pragma once

#include <cstdint>
#include <limits>

namespace atlas {

// Core type aliases - sized for performance and precision
using OrderId = uint64_t;
using Price = int64_t;         // Fixed-point: actual = Price / PRICE_MULTIPLIER
using Quantity = uint64_t;
using Timestamp = uint64_t;    // Nanoseconds since epoch
using SymbolId = uint32_t;

// Price conversion constants
constexpr int64_t PRICE_MULTIPLIER = 10000;  // 4 decimal places
constexpr Price INVALID_PRICE = std::numeric_limits<Price>::max();
constexpr OrderId INVALID_ORDER_ID = 0;

// Order side
enum class Side : uint8_t {
    Buy = 0,
    Sell = 1
};

// Order type
enum class OrderType : uint8_t {
    Limit = 0,
    Market = 1,
    IOC = 2,     // Immediate or Cancel
    FOK = 3      // Fill or Kill
};

// Order status
enum class OrderStatus : uint8_t {
    New = 0,
    PartiallyFilled = 1,
    Filled = 2,
    Cancelled = 3,
    Rejected = 4
};

// Event types for callbacks
enum class EventType : uint8_t {
    OrderAccepted = 0,
    OrderRejected = 1,
    OrderCancelled = 2,
    Trade = 3,
    BookUpdate = 4
};

// Utility functions for price conversion
[[nodiscard]] constexpr Price to_price(double d) noexcept {
    return static_cast<Price>(d * PRICE_MULTIPLIER + 0.5);  // Round to nearest
}

[[nodiscard]] constexpr double from_price(Price p) noexcept {
    return static_cast<double>(p) / PRICE_MULTIPLIER;
}

// Compare prices for same side ordering
[[nodiscard]] constexpr bool is_better_price(Price a, Price b, Side side) noexcept {
    return side == Side::Buy ? a > b : a < b;
}

// Check if prices cross (can match)
[[nodiscard]] constexpr bool prices_cross(Price bid, Price ask) noexcept {
    return bid >= ask;
}

// Opposite side
[[nodiscard]] constexpr Side opposite_side(Side side) noexcept {
    return side == Side::Buy ? Side::Sell : Side::Buy;
}

// Side to string (for debugging)
[[nodiscard]] constexpr const char* side_to_string(Side side) noexcept {
    return side == Side::Buy ? "BUY" : "SELL";
}

[[nodiscard]] constexpr const char* order_type_to_string(OrderType type) noexcept {
    switch (type) {
        case OrderType::Limit: return "LIMIT";
        case OrderType::Market: return "MARKET";
        case OrderType::IOC: return "IOC";
        case OrderType::FOK: return "FOK";
        default: return "UNKNOWN";
    }
}

[[nodiscard]] constexpr const char* order_status_to_string(OrderStatus status) noexcept {
    switch (status) {
        case OrderStatus::New: return "NEW";
        case OrderStatus::PartiallyFilled: return "PARTIAL";
        case OrderStatus::Filled: return "FILLED";
        case OrderStatus::Cancelled: return "CANCELLED";
        case OrderStatus::Rejected: return "REJECTED";
        default: return "UNKNOWN";
    }
}

}  // namespace atlas
