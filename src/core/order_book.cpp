#include "atlas/core/order_book.hpp"

#include <algorithm>
#include <cassert>

namespace atlas {

OrderBook::OrderBook(size_t pool_size) {
    order_pool_ = new PoolAllocator<Order, 100000>();
    owns_pool_ = true;
}

OrderBook::~OrderBook() {
    clear();
    if (owns_pool_) {
        delete order_pool_;
    }
}

OrderBook::OrderBook(OrderBook&& other) noexcept
    : bids_(std::move(other.bids_))
    , asks_(std::move(other.asks_))
    , order_index_(std::move(other.order_index_))
    , order_pool_(other.order_pool_)
    , owns_pool_(other.owns_pool_)
    , cached_best_bid_(other.cached_best_bid_)
    , cached_best_ask_(other.cached_best_ask_)
    , bbo_cache_valid_(other.bbo_cache_valid_)
    , total_bid_volume_(other.total_bid_volume_)
    , total_ask_volume_(other.total_ask_volume_)
    , trade_callback_(std::move(other.trade_callback_))
    , book_update_callback_(std::move(other.book_update_callback_))
    , next_trade_id_(other.next_trade_id_) {
    other.order_pool_ = nullptr;
    other.owns_pool_ = false;
}

OrderBook& OrderBook::operator=(OrderBook&& other) noexcept {
    if (this != &other) {
        clear();
        if (owns_pool_) {
            delete order_pool_;
        }

        bids_ = std::move(other.bids_);
        asks_ = std::move(other.asks_);
        order_index_ = std::move(other.order_index_);
        order_pool_ = other.order_pool_;
        owns_pool_ = other.owns_pool_;
        cached_best_bid_ = other.cached_best_bid_;
        cached_best_ask_ = other.cached_best_ask_;
        bbo_cache_valid_ = other.bbo_cache_valid_;
        total_bid_volume_ = other.total_bid_volume_;
        total_ask_volume_ = other.total_ask_volume_;
        trade_callback_ = std::move(other.trade_callback_);
        book_update_callback_ = std::move(other.book_update_callback_);
        next_trade_id_ = other.next_trade_id_;

        other.order_pool_ = nullptr;
        other.owns_pool_ = false;
    }
    return *this;
}

Order* OrderBook::add_order(OrderId id, Price price, Quantity quantity,
                            Side side, OrderType type, Timestamp timestamp) {
    // Check for duplicate order ID
    if (order_index_.find(id) != order_index_.end()) [[unlikely]] {
        return nullptr;
    }

    // Allocate order from pool
    Order* order = order_pool_->allocate();
    if (!order) [[unlikely]] {
        return nullptr;  // Pool exhausted
    }

    // Initialize order
    new (order) Order(id, price, quantity, side, type, timestamp);

    // Add to appropriate side
    if (side == Side::Buy) {
        PriceLevel& level = get_or_create_bid_level(price);
        level.add_order(order);
        total_bid_volume_ += quantity;
    } else {
        PriceLevel& level = get_or_create_ask_level(price);
        level.add_order(order);
        total_ask_volume_ += quantity;
    }

    // Add to index
    order_index_[id] = order;

    // Invalidate BBO cache
    bbo_cache_valid_ = false;

    // Notify callback
    notify_book_update(price,
        side == Side::Buy ? bids_[price].total_quantity() : asks_[price].total_quantity(),
        side);

    return order;
}

bool OrderBook::cancel_order(OrderId id) {
    auto it = order_index_.find(id);
    if (it == order_index_.end()) [[unlikely]] {
        return false;
    }

    Order* order = it->second;
    if (!order->is_active()) [[unlikely]] {
        return false;
    }

    Price price = order->price;
    Side side = order->side;
    Quantity remaining = order->remaining();

    // Remove from price level
    PriceLevel* level = order->level;
    if (level) {
        level->remove_order(order);
    }

    // Update volumes
    if (side == Side::Buy) {
        total_bid_volume_ -= remaining;
        remove_bid_level_if_empty(price);
    } else {
        total_ask_volume_ -= remaining;
        remove_ask_level_if_empty(price);
    }

    // Update order status
    order->cancel();

    // Remove from index
    order_index_.erase(it);

    // Return to pool
    order_pool_->deallocate(order);

    // Invalidate cache
    bbo_cache_valid_ = false;

    // Notify callback
    Quantity new_qty = 0;
    if (side == Side::Buy) {
        auto level_it = bids_.find(price);
        if (level_it != bids_.end()) {
            new_qty = level_it->second.total_quantity();
        }
    } else {
        auto level_it = asks_.find(price);
        if (level_it != asks_.end()) {
            new_qty = level_it->second.total_quantity();
        }
    }
    notify_book_update(price, new_qty, side);

    return true;
}

Order* OrderBook::modify_order(OrderId id, Price new_price, Quantity new_quantity) {
    auto it = order_index_.find(id);
    if (it == order_index_.end()) [[unlikely]] {
        return nullptr;
    }

    Order* old_order = it->second;
    Side side = old_order->side;
    OrderType type = old_order->type;
    Timestamp timestamp = old_order->timestamp;

    // Cancel old order
    cancel_order(id);

    // Add new order with same ID
    return add_order(id, new_price, new_quantity, side, type, timestamp);
}

Order* OrderBook::get_order(OrderId id) const {
    auto it = order_index_.find(id);
    return it != order_index_.end() ? it->second : nullptr;
}

BBO OrderBook::get_bbo() const noexcept {
    BBO bbo;

    if (!bids_.empty()) {
        const auto& best_bid_level = bids_.begin()->second;
        bbo.bid_price = best_bid_level.price();
        bbo.bid_quantity = best_bid_level.total_quantity();
    }

    if (!asks_.empty()) {
        const auto& best_ask_level = asks_.begin()->second;
        bbo.ask_price = best_ask_level.price();
        bbo.ask_quantity = best_ask_level.total_quantity();
    }

    return bbo;
}

Price OrderBook::best_bid() const noexcept {
    return bids_.empty() ? INVALID_PRICE : bids_.begin()->first;
}

Price OrderBook::best_ask() const noexcept {
    return asks_.empty() ? INVALID_PRICE : asks_.begin()->first;
}

Quantity OrderBook::best_bid_quantity() const noexcept {
    return bids_.empty() ? 0 : bids_.begin()->second.total_quantity();
}

Quantity OrderBook::best_ask_quantity() const noexcept {
    return asks_.empty() ? 0 : asks_.begin()->second.total_quantity();
}

Price OrderBook::mid_price() const noexcept {
    Price bid = best_bid();
    Price ask = best_ask();
    if (bid == INVALID_PRICE || ask == INVALID_PRICE) {
        return INVALID_PRICE;
    }
    return (bid + ask) / 2;
}

Price OrderBook::spread() const noexcept {
    Price bid = best_bid();
    Price ask = best_ask();
    if (bid == INVALID_PRICE || ask == INVALID_PRICE) {
        return INVALID_PRICE;
    }
    return ask - bid;
}

void OrderBook::get_bid_depth(std::vector<DepthLevel>& levels, size_t max_levels) const {
    levels.clear();
    levels.reserve(max_levels);

    size_t count = 0;
    for (const auto& [price, level] : bids_) {
        if (count >= max_levels) break;
        levels.push_back({price, level.total_quantity(), level.order_count()});
        ++count;
    }
}

void OrderBook::get_ask_depth(std::vector<DepthLevel>& levels, size_t max_levels) const {
    levels.clear();
    levels.reserve(max_levels);

    size_t count = 0;
    for (const auto& [price, level] : asks_) {
        if (count >= max_levels) break;
        levels.push_back({price, level.total_quantity(), level.order_count()});
        ++count;
    }
}

void OrderBook::get_depth(std::vector<DepthLevel>& bids,
                          std::vector<DepthLevel>& asks,
                          size_t max_levels) const {
    get_bid_depth(bids, max_levels);
    get_ask_depth(asks, max_levels);
}

Quantity OrderBook::total_bid_volume() const noexcept {
    return total_bid_volume_;
}

Quantity OrderBook::total_ask_volume() const noexcept {
    return total_ask_volume_;
}

size_t OrderBook::bid_level_count() const noexcept {
    return bids_.size();
}

size_t OrderBook::ask_level_count() const noexcept {
    return asks_.size();
}

size_t OrderBook::total_order_count() const noexcept {
    return order_index_.size();
}

std::optional<Price> OrderBook::calculate_vwap(Side side, Quantity target_qty) const {
    const auto& levels = (side == Side::Buy) ?
        static_cast<const std::map<Price, PriceLevel, std::greater<Price>>&>(bids_) :
        reinterpret_cast<const std::map<Price, PriceLevel, std::greater<Price>>&>(asks_);

    if (levels.empty()) {
        return std::nullopt;
    }

    Quantity remaining = target_qty;
    int64_t weighted_sum = 0;
    Quantity total_filled = 0;

    for (const auto& [price, level] : levels) {
        Quantity available = level.total_quantity();
        Quantity fill = std::min(available, remaining);

        weighted_sum += static_cast<int64_t>(price) * static_cast<int64_t>(fill);
        total_filled += fill;
        remaining -= fill;

        if (remaining == 0) break;
    }

    if (total_filled == 0) {
        return std::nullopt;
    }

    return static_cast<Price>(weighted_sum / static_cast<int64_t>(total_filled));
}

bool OrderBook::would_cross(Price price, Side side) const noexcept {
    if (side == Side::Buy) {
        Price ask = best_ask();
        return ask != INVALID_PRICE && price >= ask;
    } else {
        Price bid = best_bid();
        return bid != INVALID_PRICE && price <= bid;
    }
}

void OrderBook::set_trade_callback(TradeCallback callback) {
    trade_callback_ = std::move(callback);
}

void OrderBook::set_book_update_callback(BookUpdateCallback callback) {
    book_update_callback_ = std::move(callback);
}

void OrderBook::clear() {
    // Return all orders to pool
    for (auto& [id, order] : order_index_) {
        order_pool_->deallocate(order);
    }

    bids_.clear();
    asks_.clear();
    order_index_.clear();
    total_bid_volume_ = 0;
    total_ask_volume_ = 0;
    bbo_cache_valid_ = false;
}

bool OrderBook::empty() const noexcept {
    return order_index_.empty();
}

PriceLevel& OrderBook::get_or_create_bid_level(Price price) {
    auto [it, inserted] = bids_.try_emplace(price, price);
    return it->second;
}

PriceLevel& OrderBook::get_or_create_ask_level(Price price) {
    auto [it, inserted] = asks_.try_emplace(price, price);
    return it->second;
}

void OrderBook::remove_bid_level_if_empty(Price price) {
    auto it = bids_.find(price);
    if (it != bids_.end() && it->second.empty()) {
        bids_.erase(it);
    }
}

void OrderBook::remove_ask_level_if_empty(Price price) {
    auto it = asks_.find(price);
    if (it != asks_.end() && it->second.empty()) {
        asks_.erase(it);
    }
}

void OrderBook::notify_book_update(Price price, Quantity quantity, Side side) {
    if (book_update_callback_) {
        BookUpdate update{price, quantity, side, 0};  // TODO: add timestamp
        book_update_callback_(update);
    }
}

}  // namespace atlas
