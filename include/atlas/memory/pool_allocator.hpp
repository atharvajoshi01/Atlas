#pragma once

#include <array>
#include <atomic>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <new>
#include <type_traits>

namespace atlas {

// Cache line size for alignment
constexpr size_t CACHE_LINE_SIZE = 64;

// Aligned allocator for cache-line alignment
template <typename T, size_t Alignment = CACHE_LINE_SIZE>
class AlignedAllocator {
public:
    using value_type = T;
    using size_type = std::size_t;
    using difference_type = std::ptrdiff_t;
    using propagate_on_container_move_assignment = std::true_type;
    using is_always_equal = std::true_type;

    // Required for STL container compatibility
    template <typename U>
    struct rebind {
        using other = AlignedAllocator<U, Alignment>;
    };

    constexpr AlignedAllocator() noexcept = default;

    template <typename U>
    constexpr AlignedAllocator(const AlignedAllocator<U, Alignment>&) noexcept {}

    [[nodiscard]] T* allocate(size_type n) {
        if (n > std::numeric_limits<size_type>::max() / sizeof(T)) {
            throw std::bad_array_new_length();
        }
        // Round up size to multiple of alignment (required by POSIX aligned_alloc)
        size_type size = n * sizeof(T);
        size_type aligned_size = ((size + Alignment - 1) / Alignment) * Alignment;
        void* ptr = std::aligned_alloc(Alignment, aligned_size);
        if (!ptr) {
            throw std::bad_alloc();
        }
        return static_cast<T*>(ptr);
    }

    void deallocate(T* ptr, size_type) noexcept {
        std::free(ptr);
    }

    template <typename U>
    bool operator==(const AlignedAllocator<U, Alignment>&) const noexcept {
        return true;
    }

    template <typename U>
    bool operator!=(const AlignedAllocator<U, Alignment>&) const noexcept {
        return false;
    }
};

// Free list node - embedded in unused blocks
struct FreeListNode {
    FreeListNode* next;
};

// High-performance memory pool with zero malloc in hot path
// Pre-allocates a fixed number of objects of type T
// Uses a lock-free free list for single-threaded use (fastest)
// Thread-safe version available via atomic operations
template <typename T, size_t Capacity = 100000>
class PoolAllocator {
    static_assert(sizeof(T) >= sizeof(FreeListNode),
                  "T must be at least as large as FreeListNode");
    static_assert(Capacity > 0, "Capacity must be positive");

public:
    // Align each block to cache line to prevent false sharing
    static constexpr size_t BlockSize =
        ((sizeof(T) + CACHE_LINE_SIZE - 1) / CACHE_LINE_SIZE) * CACHE_LINE_SIZE;

    PoolAllocator() {
        // Allocate the memory pool
        pool_ = static_cast<std::byte*>(
            std::aligned_alloc(CACHE_LINE_SIZE, Capacity * BlockSize)
        );
        if (!pool_) {
            throw std::bad_alloc();
        }

        // Initialize free list - link all blocks together
        free_list_ = reinterpret_cast<FreeListNode*>(pool_);
        FreeListNode* current = free_list_;

        for (size_t i = 0; i < Capacity - 1; ++i) {
            FreeListNode* next = reinterpret_cast<FreeListNode*>(
                pool_ + (i + 1) * BlockSize
            );
            current->next = next;
            current = next;
        }
        current->next = nullptr;

        allocated_count_ = 0;
    }

    ~PoolAllocator() {
        std::free(pool_);
    }

    // Non-copyable
    PoolAllocator(const PoolAllocator&) = delete;
    PoolAllocator& operator=(const PoolAllocator&) = delete;

    // Movable
    PoolAllocator(PoolAllocator&& other) noexcept
        : pool_(other.pool_)
        , free_list_(other.free_list_)
        , allocated_count_(other.allocated_count_) {
        other.pool_ = nullptr;
        other.free_list_ = nullptr;
        other.allocated_count_ = 0;
    }

    PoolAllocator& operator=(PoolAllocator&& other) noexcept {
        if (this != &other) {
            std::free(pool_);
            pool_ = other.pool_;
            free_list_ = other.free_list_;
            allocated_count_ = other.allocated_count_;
            other.pool_ = nullptr;
            other.free_list_ = nullptr;
            other.allocated_count_ = 0;
        }
        return *this;
    }

    // Allocate a single object - O(1), no system call
    [[nodiscard]] T* allocate() noexcept {
        if (!free_list_) [[unlikely]] {
            return nullptr;  // Pool exhausted
        }

        // Pop from free list
        FreeListNode* node = free_list_;
        free_list_ = node->next;
        ++allocated_count_;

        return reinterpret_cast<T*>(node);
    }

    // Allocate and construct with arguments
    template <typename... Args>
    [[nodiscard]] T* construct(Args&&... args) noexcept(
        std::is_nothrow_constructible_v<T, Args...>
    ) {
        T* ptr = allocate();
        if (ptr) [[likely]] {
            new (ptr) T(std::forward<Args>(args)...);
        }
        return ptr;
    }

    // Deallocate a single object - O(1)
    void deallocate(T* ptr) noexcept {
        if (!ptr) [[unlikely]] {
            return;
        }

        assert(owns(ptr) && "Pointer does not belong to this pool");

        // Destroy the object
        ptr->~T();

        // Push to free list
        FreeListNode* node = reinterpret_cast<FreeListNode*>(ptr);
        node->next = free_list_;
        free_list_ = node;
        --allocated_count_;
    }

    // Check if pointer belongs to this pool
    [[nodiscard]] bool owns(const T* ptr) const noexcept {
        const auto* byte_ptr = reinterpret_cast<const std::byte*>(ptr);
        return byte_ptr >= pool_ && byte_ptr < pool_ + Capacity * BlockSize;
    }

    // Statistics
    [[nodiscard]] size_t allocated_count() const noexcept {
        return allocated_count_;
    }

    [[nodiscard]] size_t available_count() const noexcept {
        return Capacity - allocated_count_;
    }

    [[nodiscard]] static constexpr size_t capacity() noexcept {
        return Capacity;
    }

    [[nodiscard]] bool empty() const noexcept {
        return allocated_count_ == 0;
    }

    [[nodiscard]] bool full() const noexcept {
        return !free_list_;
    }

    // Reset pool - deallocate all (objects must be trivially destructible or already destroyed)
    void reset() noexcept {
        // Reinitialize free list
        free_list_ = reinterpret_cast<FreeListNode*>(pool_);
        FreeListNode* current = free_list_;

        for (size_t i = 0; i < Capacity - 1; ++i) {
            FreeListNode* next = reinterpret_cast<FreeListNode*>(
                pool_ + (i + 1) * BlockSize
            );
            current->next = next;
            current = next;
        }
        current->next = nullptr;
        allocated_count_ = 0;
    }

private:
    std::byte* pool_ = nullptr;
    FreeListNode* free_list_ = nullptr;
    size_t allocated_count_ = 0;
};

// Thread-safe version using atomics (slightly slower but safe for multi-threaded use)
template <typename T, size_t Capacity = 100000>
class AtomicPoolAllocator {
    static_assert(sizeof(T) >= sizeof(FreeListNode),
                  "T must be at least as large as FreeListNode");
    static_assert(Capacity > 0, "Capacity must be positive");

public:
    static constexpr size_t BlockSize =
        ((sizeof(T) + CACHE_LINE_SIZE - 1) / CACHE_LINE_SIZE) * CACHE_LINE_SIZE;

    AtomicPoolAllocator() {
        pool_ = static_cast<std::byte*>(
            std::aligned_alloc(CACHE_LINE_SIZE, Capacity * BlockSize)
        );
        if (!pool_) {
            throw std::bad_alloc();
        }

        // Initialize free list
        FreeListNode* head = reinterpret_cast<FreeListNode*>(pool_);
        FreeListNode* current = head;

        for (size_t i = 0; i < Capacity - 1; ++i) {
            FreeListNode* next = reinterpret_cast<FreeListNode*>(
                pool_ + (i + 1) * BlockSize
            );
            current->next = next;
            current = next;
        }
        current->next = nullptr;

        free_list_.store(head, std::memory_order_relaxed);
        allocated_count_.store(0, std::memory_order_relaxed);
    }

    ~AtomicPoolAllocator() {
        std::free(pool_);
    }

    // Non-copyable, non-movable (due to atomics)
    AtomicPoolAllocator(const AtomicPoolAllocator&) = delete;
    AtomicPoolAllocator& operator=(const AtomicPoolAllocator&) = delete;
    AtomicPoolAllocator(AtomicPoolAllocator&&) = delete;
    AtomicPoolAllocator& operator=(AtomicPoolAllocator&&) = delete;

    // Thread-safe allocate using CAS
    [[nodiscard]] T* allocate() noexcept {
        FreeListNode* old_head = free_list_.load(std::memory_order_acquire);

        while (old_head) {
            FreeListNode* new_head = old_head->next;
            if (free_list_.compare_exchange_weak(
                    old_head, new_head,
                    std::memory_order_release,
                    std::memory_order_acquire)) {
                allocated_count_.fetch_add(1, std::memory_order_relaxed);
                return reinterpret_cast<T*>(old_head);
            }
            // CAS failed, old_head updated by compare_exchange_weak
        }

        return nullptr;  // Pool exhausted
    }

    // Thread-safe deallocate using CAS
    void deallocate(T* ptr) noexcept {
        if (!ptr) [[unlikely]] {
            return;
        }

        ptr->~T();

        FreeListNode* node = reinterpret_cast<FreeListNode*>(ptr);
        FreeListNode* old_head = free_list_.load(std::memory_order_acquire);

        do {
            node->next = old_head;
        } while (!free_list_.compare_exchange_weak(
            old_head, node,
            std::memory_order_release,
            std::memory_order_acquire));

        allocated_count_.fetch_sub(1, std::memory_order_relaxed);
    }

    [[nodiscard]] size_t allocated_count() const noexcept {
        return allocated_count_.load(std::memory_order_relaxed);
    }

    [[nodiscard]] static constexpr size_t capacity() noexcept {
        return Capacity;
    }

private:
    alignas(CACHE_LINE_SIZE) std::byte* pool_ = nullptr;
    alignas(CACHE_LINE_SIZE) std::atomic<FreeListNode*> free_list_{nullptr};
    alignas(CACHE_LINE_SIZE) std::atomic<size_t> allocated_count_{0};
};

}  // namespace atlas
