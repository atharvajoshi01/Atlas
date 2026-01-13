#pragma once

#include "atlas/memory/pool_allocator.hpp"

#include <array>
#include <atomic>
#include <cassert>
#include <cstddef>
#include <optional>
#include <type_traits>

namespace atlas {

// Single-Producer Single-Consumer (SPSC) lock-free ring buffer
// Optimized for low-latency market data processing
// Uses memory barriers for correct ordering without locks
template <typename T, size_t Capacity = 65536>
class SPSCRingBuffer {
    static_assert((Capacity & (Capacity - 1)) == 0,
                  "Capacity must be a power of 2 for fast modulo");
    static_assert(Capacity > 0, "Capacity must be positive");
    static_assert(std::is_trivially_copyable_v<T>,
                  "T must be trivially copyable for lock-free operations");

public:
    SPSCRingBuffer() = default;

    // Non-copyable
    SPSCRingBuffer(const SPSCRingBuffer&) = delete;
    SPSCRingBuffer& operator=(const SPSCRingBuffer&) = delete;

    // Try to push an item (producer side)
    // Returns true if successful, false if buffer is full
    [[nodiscard]] bool try_push(const T& item) noexcept {
        const size_t write_pos = write_pos_.load(std::memory_order_relaxed);
        const size_t next_write = (write_pos + 1) & MASK;

        // Check if buffer is full
        if (next_write == read_pos_.load(std::memory_order_acquire)) [[unlikely]] {
            return false;
        }

        buffer_[write_pos] = item;
        write_pos_.store(next_write, std::memory_order_release);
        return true;
    }

    // Try to push with move semantics
    [[nodiscard]] bool try_push(T&& item) noexcept {
        const size_t write_pos = write_pos_.load(std::memory_order_relaxed);
        const size_t next_write = (write_pos + 1) & MASK;

        if (next_write == read_pos_.load(std::memory_order_acquire)) [[unlikely]] {
            return false;
        }

        buffer_[write_pos] = std::move(item);
        write_pos_.store(next_write, std::memory_order_release);
        return true;
    }

    // Try to pop an item (consumer side)
    // Returns true if successful, false if buffer is empty
    [[nodiscard]] bool try_pop(T& item) noexcept {
        const size_t read_pos = read_pos_.load(std::memory_order_relaxed);

        // Check if buffer is empty
        if (read_pos == write_pos_.load(std::memory_order_acquire)) [[unlikely]] {
            return false;
        }

        item = buffer_[read_pos];
        read_pos_.store((read_pos + 1) & MASK, std::memory_order_release);
        return true;
    }

    // Try to pop and return optional
    [[nodiscard]] std::optional<T> try_pop() noexcept {
        T item;
        if (try_pop(item)) {
            return item;
        }
        return std::nullopt;
    }

    // Peek at front item without removing (consumer side)
    [[nodiscard]] const T* peek() const noexcept {
        const size_t read_pos = read_pos_.load(std::memory_order_relaxed);
        if (read_pos == write_pos_.load(std::memory_order_acquire)) {
            return nullptr;
        }
        return &buffer_[read_pos];
    }

    // Get current size (approximate, may change during call)
    [[nodiscard]] size_t size() const noexcept {
        const size_t write = write_pos_.load(std::memory_order_acquire);
        const size_t read = read_pos_.load(std::memory_order_acquire);
        return (write - read + Capacity) & MASK;
    }

    // Check if empty (approximate)
    [[nodiscard]] bool empty() const noexcept {
        return read_pos_.load(std::memory_order_acquire) ==
               write_pos_.load(std::memory_order_acquire);
    }

    // Check if full (approximate)
    [[nodiscard]] bool full() const noexcept {
        const size_t write = write_pos_.load(std::memory_order_acquire);
        const size_t read = read_pos_.load(std::memory_order_acquire);
        return ((write + 1) & MASK) == read;
    }

    // Get capacity
    [[nodiscard]] static constexpr size_t capacity() noexcept {
        return Capacity - 1;  // One slot is always empty to distinguish full from empty
    }

    // Clear the buffer (only safe when no concurrent access)
    void clear() noexcept {
        read_pos_.store(0, std::memory_order_relaxed);
        write_pos_.store(0, std::memory_order_relaxed);
    }

private:
    static constexpr size_t MASK = Capacity - 1;

    // Padding to prevent false sharing between producer and consumer
    alignas(CACHE_LINE_SIZE) std::atomic<size_t> write_pos_{0};
    alignas(CACHE_LINE_SIZE) std::atomic<size_t> read_pos_{0};
    alignas(CACHE_LINE_SIZE) std::array<T, Capacity> buffer_{};
};

// Multi-Producer Single-Consumer (MPSC) variant
// Uses CAS for producer synchronization
template <typename T, size_t Capacity = 65536>
class MPSCRingBuffer {
    static_assert((Capacity & (Capacity - 1)) == 0,
                  "Capacity must be a power of 2");

public:
    MPSCRingBuffer() = default;

    MPSCRingBuffer(const MPSCRingBuffer&) = delete;
    MPSCRingBuffer& operator=(const MPSCRingBuffer&) = delete;

    // Try to push (multiple producers safe)
    [[nodiscard]] bool try_push(const T& item) noexcept {
        size_t write_pos = write_pos_.load(std::memory_order_relaxed);

        while (true) {
            const size_t next_write = (write_pos + 1) & MASK;

            // Check if full
            if (next_write == read_pos_.load(std::memory_order_acquire)) [[unlikely]] {
                return false;
            }

            // Try to claim the slot
            if (write_pos_.compare_exchange_weak(
                    write_pos, next_write,
                    std::memory_order_acq_rel,
                    std::memory_order_relaxed)) {
                buffer_[write_pos] = item;
                // Mark slot as ready (could use separate ready flags for better ordering)
                return true;
            }
            // CAS failed, write_pos updated by compare_exchange_weak
        }
    }

    // Try to pop (single consumer only)
    [[nodiscard]] bool try_pop(T& item) noexcept {
        const size_t read_pos = read_pos_.load(std::memory_order_relaxed);

        if (read_pos == write_pos_.load(std::memory_order_acquire)) [[unlikely]] {
            return false;
        }

        item = buffer_[read_pos];
        read_pos_.store((read_pos + 1) & MASK, std::memory_order_release);
        return true;
    }

    [[nodiscard]] size_t size() const noexcept {
        const size_t write = write_pos_.load(std::memory_order_acquire);
        const size_t read = read_pos_.load(std::memory_order_acquire);
        return (write - read + Capacity) & MASK;
    }

    [[nodiscard]] bool empty() const noexcept {
        return read_pos_.load(std::memory_order_acquire) ==
               write_pos_.load(std::memory_order_acquire);
    }

private:
    static constexpr size_t MASK = Capacity - 1;

    alignas(CACHE_LINE_SIZE) std::atomic<size_t> write_pos_{0};
    alignas(CACHE_LINE_SIZE) std::atomic<size_t> read_pos_{0};
    alignas(CACHE_LINE_SIZE) std::array<T, Capacity> buffer_{};
};

}  // namespace atlas
