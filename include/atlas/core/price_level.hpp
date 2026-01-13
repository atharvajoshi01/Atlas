#pragma once

#include "atlas/core/types.hpp"
#include "atlas/core/order.hpp"

#include <cassert>
#include <cstddef>

namespace atlas {

// PriceLevel maintains all orders at a single price point
// Uses an intrusive doubly-linked list for O(1) add/remove
// Orders are maintained in FIFO order (price-time priority)
class PriceLevel {
public:
    PriceLevel() = default;

    explicit PriceLevel(Price price) noexcept : price_(price) {}

    // Non-copyable but movable
    PriceLevel(const PriceLevel&) = delete;
    PriceLevel& operator=(const PriceLevel&) = delete;

    PriceLevel(PriceLevel&& other) noexcept
        : price_(other.price_)
        , total_quantity_(other.total_quantity_)
        , order_count_(other.order_count_)
        , head_(other.head_)
        , tail_(other.tail_) {
        other.price_ = INVALID_PRICE;
        other.total_quantity_ = 0;
        other.order_count_ = 0;
        other.head_ = nullptr;
        other.tail_ = nullptr;

        // Update level pointers in all orders
        for (Order* order = head_; order != nullptr; order = order->next) {
            order->level = this;
        }
    }

    PriceLevel& operator=(PriceLevel&& other) noexcept {
        if (this != &other) {
            price_ = other.price_;
            total_quantity_ = other.total_quantity_;
            order_count_ = other.order_count_;
            head_ = other.head_;
            tail_ = other.tail_;

            other.price_ = INVALID_PRICE;
            other.total_quantity_ = 0;
            other.order_count_ = 0;
            other.head_ = nullptr;
            other.tail_ = nullptr;

            for (Order* order = head_; order != nullptr; order = order->next) {
                order->level = this;
            }
        }
        return *this;
    }

    // Add order to the back of the queue (FIFO)
    // O(1) operation
    void add_order(Order* order) noexcept {
        assert(order != nullptr);
        assert(order->price == price_ || price_ == INVALID_PRICE);

        if (price_ == INVALID_PRICE) {
            price_ = order->price;
        }

        order->level = this;
        order->prev = tail_;
        order->next = nullptr;

        if (tail_) {
            tail_->next = order;
        } else {
            head_ = order;
        }
        tail_ = order;

        total_quantity_ += order->remaining();
        ++order_count_;
    }

    // Remove order from the queue
    // O(1) operation using intrusive list pointers
    void remove_order(Order* order) noexcept {
        assert(order != nullptr);
        assert(order->level == this);

        // Update quantity
        total_quantity_ -= order->remaining();

        // Update list pointers
        if (order->prev) {
            order->prev->next = order->next;
        } else {
            head_ = order->next;
        }

        if (order->next) {
            order->next->prev = order->prev;
        } else {
            tail_ = order->prev;
        }

        order->prev = nullptr;
        order->next = nullptr;
        order->level = nullptr;
        --order_count_;
    }

    // Reduce quantity of an order (after partial fill)
    void reduce_quantity(Quantity amount) noexcept {
        assert(amount <= total_quantity_);
        total_quantity_ -= amount;
    }

    // Get the first order in the queue (best time priority)
    [[nodiscard]] Order* front() const noexcept {
        return head_;
    }

    // Get the last order in the queue
    [[nodiscard]] Order* back() const noexcept {
        return tail_;
    }

    // Accessors
    [[nodiscard]] Price price() const noexcept {
        return price_;
    }

    [[nodiscard]] Quantity total_quantity() const noexcept {
        return total_quantity_;
    }

    [[nodiscard]] size_t order_count() const noexcept {
        return order_count_;
    }

    [[nodiscard]] bool empty() const noexcept {
        return head_ == nullptr;
    }

    // Iterator support for range-based for loops
    class Iterator {
    public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = Order;
        using difference_type = std::ptrdiff_t;
        using pointer = Order*;
        using reference = Order&;

        explicit Iterator(Order* order) noexcept : current_(order) {}

        reference operator*() const noexcept { return *current_; }
        pointer operator->() const noexcept { return current_; }

        Iterator& operator++() noexcept {
            current_ = current_->next;
            return *this;
        }

        Iterator operator++(int) noexcept {
            Iterator tmp = *this;
            ++(*this);
            return tmp;
        }

        bool operator==(const Iterator& other) const noexcept {
            return current_ == other.current_;
        }

        bool operator!=(const Iterator& other) const noexcept {
            return current_ != other.current_;
        }

    private:
        Order* current_;
    };

    [[nodiscard]] Iterator begin() const noexcept { return Iterator(head_); }
    [[nodiscard]] Iterator end() const noexcept { return Iterator(nullptr); }

private:
    Price price_{INVALID_PRICE};
    Quantity total_quantity_{0};
    size_t order_count_{0};
    Order* head_{nullptr};
    Order* tail_{nullptr};
};

}  // namespace atlas
