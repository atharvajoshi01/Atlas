#include <gtest/gtest.h>
#include "atlas/feed/ring_buffer.hpp"

#include <atomic>
#include <thread>
#include <vector>

using namespace atlas;

// Simple test message
struct TestMessage {
    uint64_t sequence;
    uint64_t timestamp;
    double value;
};

class RingBufferTest : public ::testing::Test {
protected:
    static constexpr size_t CAPACITY = 1024;  // Must be power of 2
    SPSCRingBuffer<TestMessage, CAPACITY> buffer;
};

// Basic operations
TEST_F(RingBufferTest, InitiallyEmpty) {
    EXPECT_TRUE(buffer.empty());
    EXPECT_FALSE(buffer.full());
    EXPECT_EQ(buffer.size(), 0);
}

TEST_F(RingBufferTest, PushSingle) {
    TestMessage msg{1, 100, 3.14};
    bool pushed = buffer.try_push(msg);

    EXPECT_TRUE(pushed);
    EXPECT_FALSE(buffer.empty());
    EXPECT_EQ(buffer.size(), 1);
}

TEST_F(RingBufferTest, PopSingle) {
    TestMessage msg{1, 100, 3.14};
    buffer.try_push(msg);

    TestMessage popped;
    bool success = buffer.try_pop(popped);

    EXPECT_TRUE(success);
    EXPECT_EQ(popped.sequence, 1);
    EXPECT_EQ(popped.timestamp, 100);
    EXPECT_DOUBLE_EQ(popped.value, 3.14);
    EXPECT_TRUE(buffer.empty());
}

TEST_F(RingBufferTest, PopFromEmpty) {
    TestMessage msg;
    bool success = buffer.try_pop(msg);

    EXPECT_FALSE(success);
}

TEST_F(RingBufferTest, PushUntilFull) {
    // Capacity - 1 because one slot is used to distinguish full from empty
    for (size_t i = 0; i < buffer.capacity(); ++i) {
        TestMessage msg{i, i * 10, static_cast<double>(i)};
        bool pushed = buffer.try_push(msg);
        EXPECT_TRUE(pushed) << "Failed at iteration " << i;
    }

    EXPECT_TRUE(buffer.full());

    // Next push should fail
    TestMessage overflow{999, 999, 999.0};
    EXPECT_FALSE(buffer.try_push(overflow));
}

TEST_F(RingBufferTest, FIFOOrder) {
    const int COUNT = 100;

    for (int i = 0; i < COUNT; ++i) {
        TestMessage msg{static_cast<uint64_t>(i), 0, 0.0};
        buffer.try_push(msg);
    }

    for (int i = 0; i < COUNT; ++i) {
        TestMessage msg;
        buffer.try_pop(msg);
        EXPECT_EQ(msg.sequence, static_cast<uint64_t>(i));
    }
}

TEST_F(RingBufferTest, Peek) {
    TestMessage msg{42, 100, 1.5};
    buffer.try_push(msg);

    const TestMessage* peeked = buffer.peek();
    ASSERT_NE(peeked, nullptr);
    EXPECT_EQ(peeked->sequence, 42);

    // Peek should not remove the item
    EXPECT_EQ(buffer.size(), 1);

    TestMessage popped;
    buffer.try_pop(popped);
    EXPECT_EQ(popped.sequence, 42);
}

TEST_F(RingBufferTest, PeekEmpty) {
    const TestMessage* peeked = buffer.peek();
    EXPECT_EQ(peeked, nullptr);
}

TEST_F(RingBufferTest, TryPopOptional) {
    TestMessage msg{42, 100, 1.5};
    buffer.try_push(msg);

    auto result = buffer.try_pop();
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->sequence, 42);

    auto empty_result = buffer.try_pop();
    EXPECT_FALSE(empty_result.has_value());
}

TEST_F(RingBufferTest, Clear) {
    for (int i = 0; i < 100; ++i) {
        TestMessage msg{static_cast<uint64_t>(i), 0, 0.0};
        buffer.try_push(msg);
    }

    buffer.clear();

    EXPECT_TRUE(buffer.empty());
    EXPECT_EQ(buffer.size(), 0);
}

TEST_F(RingBufferTest, WrapAround) {
    // Fill almost to capacity
    for (size_t i = 0; i < buffer.capacity() - 10; ++i) {
        TestMessage msg{i, 0, 0.0};
        buffer.try_push(msg);
    }

    // Pop half
    for (size_t i = 0; i < buffer.capacity() / 2; ++i) {
        TestMessage msg;
        buffer.try_pop(msg);
    }

    // Push more (should wrap around)
    for (size_t i = 0; i < buffer.capacity() / 2; ++i) {
        TestMessage msg{1000 + i, 0, 0.0};
        bool pushed = buffer.try_push(msg);
        EXPECT_TRUE(pushed);
    }

    // Verify we can still pop in order
    TestMessage msg;
    buffer.try_pop(msg);
    EXPECT_GE(msg.sequence, buffer.capacity() / 2 - 10);
}

// Concurrent tests
TEST_F(RingBufferTest, ProducerConsumer) {
    const int NUM_MESSAGES = 100000;
    std::atomic<bool> done{false};
    std::atomic<int> consumed{0};

    // Consumer thread
    std::thread consumer([this, &done, &consumed, NUM_MESSAGES]() {
        uint64_t expected = 0;
        while (consumed < NUM_MESSAGES) {
            TestMessage msg;
            if (buffer.try_pop(msg)) {
                EXPECT_EQ(msg.sequence, expected);
                expected++;
                consumed++;
            }
        }
    });

    // Producer thread (this thread)
    for (int i = 0; i < NUM_MESSAGES; ++i) {
        TestMessage msg{static_cast<uint64_t>(i), 0, 0.0};
        while (!buffer.try_push(msg)) {
            std::this_thread::yield();  // Buffer full, wait
        }
    }

    consumer.join();
    EXPECT_EQ(consumed, NUM_MESSAGES);
}

// MPSC buffer tests
class MPSCRingBufferTest : public ::testing::Test {
protected:
    static constexpr size_t CAPACITY = 4096;
    MPSCRingBuffer<TestMessage, CAPACITY> buffer;
};

TEST_F(MPSCRingBufferTest, SingleProducer) {
    TestMessage msg{1, 100, 3.14};
    bool pushed = buffer.try_push(msg);

    EXPECT_TRUE(pushed);
    EXPECT_FALSE(buffer.empty());
}

TEST_F(MPSCRingBufferTest, MultipleProducers) {
    const int NUM_THREADS = 4;
    const int MSGS_PER_THREAD = 1000;

    std::vector<std::thread> producers;
    std::atomic<int> produced{0};

    for (int t = 0; t < NUM_THREADS; ++t) {
        producers.emplace_back([this, t, &produced]() {
            for (int i = 0; i < MSGS_PER_THREAD; ++i) {
                TestMessage msg{
                    static_cast<uint64_t>(t * MSGS_PER_THREAD + i),
                    0, 0.0
                };
                while (!buffer.try_push(msg)) {
                    std::this_thread::yield();
                }
                produced++;
            }
        });
    }

    // Consumer
    int consumed = 0;
    while (consumed < NUM_THREADS * MSGS_PER_THREAD) {
        TestMessage msg;
        if (buffer.try_pop(msg)) {
            consumed++;
        } else {
            std::this_thread::yield();
        }
    }

    for (auto& t : producers) {
        t.join();
    }

    EXPECT_EQ(consumed, NUM_THREADS * MSGS_PER_THREAD);
    EXPECT_TRUE(buffer.empty());
}

// Capacity tests
TEST(RingBufferCapacity, StaticCapacity) {
    SPSCRingBuffer<int, 256> small_buffer;
    SPSCRingBuffer<int, 65536> large_buffer;

    EXPECT_EQ(small_buffer.capacity(), 255);   // Capacity - 1
    EXPECT_EQ(large_buffer.capacity(), 65535);
}
