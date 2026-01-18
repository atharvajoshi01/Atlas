#include <gtest/gtest.h>
#include "atlas/memory/pool_allocator.hpp"

#include <cstring>
#include <thread>
#include <vector>

using namespace atlas;

// Test object for pool allocation
struct TestObject {
    uint64_t id;
    double value;
    char data[32];

    TestObject() : id(0), value(0.0) {
        std::memset(data, 0, sizeof(data));
    }

    TestObject(uint64_t id_, double value_) : id(id_), value(value_) {
        std::memset(data, 0, sizeof(data));
    }
};

class PoolAllocatorTest : public ::testing::Test {
protected:
    static constexpr size_t POOL_SIZE = 1000;
    PoolAllocator<TestObject, POOL_SIZE> pool;
};

// Basic allocation
TEST_F(PoolAllocatorTest, AllocateSingle) {
    TestObject* obj = pool.allocate();

    ASSERT_NE(obj, nullptr);
    EXPECT_TRUE(pool.owns(obj));
    EXPECT_EQ(pool.allocated_count(), 1);
    EXPECT_EQ(pool.available_count(), POOL_SIZE - 1);
}

TEST_F(PoolAllocatorTest, ConstructWithArgs) {
    TestObject* obj = pool.construct(42, 3.14);

    ASSERT_NE(obj, nullptr);
    EXPECT_EQ(obj->id, 42);
    EXPECT_DOUBLE_EQ(obj->value, 3.14);
}

TEST_F(PoolAllocatorTest, Deallocate) {
    TestObject* obj = pool.allocate();
    pool.deallocate(obj);

    EXPECT_EQ(pool.allocated_count(), 0);
    EXPECT_EQ(pool.available_count(), POOL_SIZE);
}

TEST_F(PoolAllocatorTest, AllocateMultiple) {
    std::vector<TestObject*> objects;

    for (size_t i = 0; i < 100; ++i) {
        TestObject* obj = pool.construct(i, static_cast<double>(i));
        ASSERT_NE(obj, nullptr);
        objects.push_back(obj);
    }

    EXPECT_EQ(pool.allocated_count(), 100);

    // Verify all objects are valid
    for (size_t i = 0; i < objects.size(); ++i) {
        EXPECT_EQ(objects[i]->id, i);
        EXPECT_TRUE(pool.owns(objects[i]));
    }
}

TEST_F(PoolAllocatorTest, AllocateUntilFull) {
    std::vector<TestObject*> objects;

    for (size_t i = 0; i < POOL_SIZE; ++i) {
        TestObject* obj = pool.allocate();
        ASSERT_NE(obj, nullptr);
        objects.push_back(obj);
    }

    EXPECT_TRUE(pool.full());
    EXPECT_EQ(pool.allocated_count(), POOL_SIZE);

    // Next allocation should fail
    TestObject* overflow = pool.allocate();
    EXPECT_EQ(overflow, nullptr);
}

TEST_F(PoolAllocatorTest, ReuseAfterDeallocation) {
    TestObject* obj1 = pool.allocate();
    TestObject* addr1 = obj1;

    pool.deallocate(obj1);

    TestObject* obj2 = pool.allocate();
    // Should reuse the same memory
    EXPECT_EQ(obj2, addr1);
}

TEST_F(PoolAllocatorTest, DeallocateNull) {
    // Should not crash
    pool.deallocate(nullptr);
    EXPECT_EQ(pool.allocated_count(), 0);
}

TEST_F(PoolAllocatorTest, CacheLineAlignment) {
    TestObject* obj = pool.allocate();
    uintptr_t addr = reinterpret_cast<uintptr_t>(obj);

    EXPECT_EQ(addr % CACHE_LINE_SIZE, 0);
}

TEST_F(PoolAllocatorTest, Reset) {
    for (size_t i = 0; i < 100; ++i) {
        pool.allocate();
    }

    pool.reset();

    EXPECT_TRUE(pool.empty());
    EXPECT_EQ(pool.allocated_count(), 0);
}

TEST_F(PoolAllocatorTest, InitiallyEmpty) {
    EXPECT_TRUE(pool.empty());
    EXPECT_FALSE(pool.full());
    EXPECT_EQ(pool.allocated_count(), 0);
    EXPECT_EQ(pool.available_count(), POOL_SIZE);
}

// AtomicPoolAllocator tests
class AtomicPoolAllocatorTest : public ::testing::Test {
protected:
    static constexpr size_t POOL_SIZE = 1000;
    AtomicPoolAllocator<TestObject, POOL_SIZE> pool;
};

TEST_F(AtomicPoolAllocatorTest, AllocateSingle) {
    TestObject* obj = pool.allocate();

    ASSERT_NE(obj, nullptr);
    EXPECT_EQ(pool.allocated_count(), 1);
}

TEST_F(AtomicPoolAllocatorTest, ConcurrentAllocation) {
    const int NUM_THREADS = 4;
    const int ALLOCS_PER_THREAD = 100;

    std::vector<std::thread> threads;
    std::vector<std::vector<TestObject*>> thread_objects(NUM_THREADS);

    for (int t = 0; t < NUM_THREADS; ++t) {
        threads.emplace_back([this, t, &thread_objects]() {
            for (int i = 0; i < ALLOCS_PER_THREAD; ++i) {
                TestObject* obj = pool.allocate();
                if (obj) {
                    thread_objects[t].push_back(obj);
                }
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    // Count total allocations
    size_t total = 0;
    for (const auto& objs : thread_objects) {
        total += objs.size();
    }

    EXPECT_EQ(total, NUM_THREADS * ALLOCS_PER_THREAD);
    EXPECT_EQ(pool.allocated_count(), total);
}

TEST_F(AtomicPoolAllocatorTest, ConcurrentAllocateAndDeallocate) {
    const int NUM_THREADS = 4;
    const int OPS_PER_THREAD = 1000;

    std::atomic<int> alloc_count{0};
    std::atomic<int> dealloc_count{0};

    std::vector<std::thread> threads;

    for (int t = 0; t < NUM_THREADS; ++t) {
        threads.emplace_back([this, t, &alloc_count, &dealloc_count]() {
            std::vector<TestObject*> local_objects;

            for (int i = 0; i < OPS_PER_THREAD; ++i) {
                // Alternate between alloc and dealloc
                if (i % 2 == 0 || local_objects.empty()) {
                    TestObject* obj = pool.allocate();
                    if (obj) {
                        local_objects.push_back(obj);
                        alloc_count++;
                    }
                } else {
                    TestObject* obj = local_objects.back();
                    local_objects.pop_back();
                    pool.deallocate(obj);
                    dealloc_count++;
                }
            }

            // Clean up remaining
            for (auto* obj : local_objects) {
                pool.deallocate(obj);
                dealloc_count++;
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    EXPECT_EQ(alloc_count.load(), dealloc_count.load());
    EXPECT_EQ(pool.allocated_count(), 0);
}

// AlignedAllocator tests
TEST(AlignedAllocatorTest, Alignment) {
    AlignedAllocator<double, 64> alloc;
    double* ptr = alloc.allocate(10);

    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    EXPECT_EQ(addr % 64, 0);

    alloc.deallocate(ptr, 10);
}

TEST(AlignedAllocatorTest, WithVector) {
    std::vector<double, AlignedAllocator<double, 64>> vec;
    vec.resize(100);

    uintptr_t addr = reinterpret_cast<uintptr_t>(vec.data());
    EXPECT_EQ(addr % 64, 0);
}
