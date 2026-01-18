#include <benchmark/benchmark.h>
#include "atlas/feed/itch_parser.hpp"
#include "atlas/feed/itch_handler.hpp"

#include <random>
#include <vector>

using namespace atlas;
using namespace atlas::itch;

// Helper to create big-endian bytes
class MessageGenerator {
public:
    MessageGenerator() : rng_(42) {}  // Fixed seed for reproducibility

    void add_byte(uint8_t b) { data_.push_back(b); }
    void add_be16(uint16_t val) {
        data_.push_back(static_cast<uint8_t>(val >> 8));
        data_.push_back(static_cast<uint8_t>(val));
    }
    void add_be32(uint32_t val) {
        data_.push_back(static_cast<uint8_t>(val >> 24));
        data_.push_back(static_cast<uint8_t>(val >> 16));
        data_.push_back(static_cast<uint8_t>(val >> 8));
        data_.push_back(static_cast<uint8_t>(val));
    }
    void add_be48(uint64_t val) {
        data_.push_back(static_cast<uint8_t>(val >> 40));
        data_.push_back(static_cast<uint8_t>(val >> 32));
        data_.push_back(static_cast<uint8_t>(val >> 24));
        data_.push_back(static_cast<uint8_t>(val >> 16));
        data_.push_back(static_cast<uint8_t>(val >> 8));
        data_.push_back(static_cast<uint8_t>(val));
    }
    void add_be64(uint64_t val) {
        data_.push_back(static_cast<uint8_t>(val >> 56));
        data_.push_back(static_cast<uint8_t>(val >> 48));
        data_.push_back(static_cast<uint8_t>(val >> 40));
        data_.push_back(static_cast<uint8_t>(val >> 32));
        data_.push_back(static_cast<uint8_t>(val >> 24));
        data_.push_back(static_cast<uint8_t>(val >> 16));
        data_.push_back(static_cast<uint8_t>(val >> 8));
        data_.push_back(static_cast<uint8_t>(val));
    }
    void add_string(const char* s, size_t len) {
        for (size_t i = 0; i < len; ++i) {
            data_.push_back(s[i] ? static_cast<uint8_t>(s[i]) : ' ');
        }
    }

    // Generate Add Order message
    void generate_add_order(uint64_t order_ref, bool is_buy, uint32_t shares,
                           const char* symbol, uint32_t price) {
        add_byte('A');
        add_be16(1);                    // Stock locate
        add_be16(0);                    // Tracking number
        add_be48(timestamp_++);         // Timestamp
        add_be64(order_ref);
        add_byte(is_buy ? 'B' : 'S');
        add_be32(shares);
        add_string(symbol, 8);
        add_be32(price);
    }

    // Generate Order Delete message
    void generate_order_delete(uint64_t order_ref) {
        add_byte('D');
        add_be16(1);
        add_be16(0);
        add_be48(timestamp_++);
        add_be64(order_ref);
    }

    // Generate Order Execute message
    void generate_order_executed(uint64_t order_ref, uint32_t shares) {
        add_byte('E');
        add_be16(1);
        add_be16(0);
        add_be48(timestamp_++);
        add_be64(order_ref);
        add_be32(shares);
        add_be64(match_number_++);
    }

    // Generate realistic message stream
    std::vector<uint8_t> generate_message_stream(size_t num_messages) {
        data_.clear();
        data_.reserve(num_messages * 40);  // Avg message size ~40 bytes

        std::uniform_int_distribution<int> action_dist(0, 9);
        std::uniform_int_distribution<uint32_t> price_dist(1000000, 2000000);
        std::uniform_int_distribution<uint32_t> qty_dist(1, 1000);

        const char* symbols[] = {"AAPL    ", "MSFT    ", "GOOGL   ", "AMZN    ", "NVDA    "};

        uint64_t next_order_id = 1;
        std::vector<uint64_t> active_orders;

        for (size_t i = 0; i < num_messages; ++i) {
            int action = action_dist(rng_);

            if (action < 6 || active_orders.empty()) {
                // 60% add orders (or 100% if no active orders)
                generate_add_order(next_order_id, action % 2 == 0,
                                  qty_dist(rng_), symbols[action % 5], price_dist(rng_));
                active_orders.push_back(next_order_id);
                ++next_order_id;
            } else if (action < 8) {
                // 20% delete orders
                std::uniform_int_distribution<size_t> idx_dist(0, active_orders.size() - 1);
                size_t idx = idx_dist(rng_);
                generate_order_delete(active_orders[idx]);
                active_orders.erase(active_orders.begin() + static_cast<std::ptrdiff_t>(idx));
            } else {
                // 20% execute orders
                std::uniform_int_distribution<size_t> idx_dist(0, active_orders.size() - 1);
                size_t idx = idx_dist(rng_);
                generate_order_executed(active_orders[idx], qty_dist(rng_) / 2 + 1);
            }
        }

        return data_;
    }

    const std::vector<uint8_t>& data() const { return data_; }

private:
    std::vector<uint8_t> data_;
    std::mt19937 rng_;
    uint64_t timestamp_ = 34200000000000;  // 9:30 AM in nanoseconds
    uint64_t match_number_ = 1;
};

// Benchmark: Parse single Add Order message
static void BM_ITCH_ParseAddOrder(benchmark::State& state) {
    MessageGenerator gen;
    gen.generate_add_order(12345, true, 100, "AAPL    ", 1500000);
    const auto& data = gen.data();

    Parser parser;
    uint64_t orders_parsed = 0;
    parser.on_add_order([&](const AddOrder&) { ++orders_parsed; });

    for (auto _ : state) {
        parser.parse_message(data.data(), data.size());
    }

    state.SetItemsProcessed(state.iterations());
    state.SetBytesProcessed(state.iterations() * 36);
}
BENCHMARK(BM_ITCH_ParseAddOrder);

// Benchmark: Parse message stream
static void BM_ITCH_ParseMessageStream(benchmark::State& state) {
    const size_t num_messages = static_cast<size_t>(state.range(0));

    MessageGenerator gen;
    auto data = gen.generate_message_stream(num_messages);

    Parser parser;
    parser.on_add_order([](const AddOrder&) {});
    parser.on_order_delete([](const OrderDelete&) {});
    parser.on_order_executed([](const OrderExecuted&) {});

    for (auto _ : state) {
        parser.reset_stats();
        parser.parse_messages(data.data(), data.size());
        benchmark::DoNotOptimize(parser.messages_parsed());
    }

    state.SetItemsProcessed(state.iterations() * num_messages);
    state.SetBytesProcessed(state.iterations() * static_cast<int64_t>(data.size()));
}
BENCHMARK(BM_ITCH_ParseMessageStream)->Arg(1000)->Arg(10000)->Arg(100000);

// Benchmark: Full handler with order book updates
static void BM_ITCH_HandlerWithOrderBook(benchmark::State& state) {
    const size_t num_messages = static_cast<size_t>(state.range(0));

    MessageGenerator gen;
    auto data = gen.generate_message_stream(num_messages);

    for (auto _ : state) {
        ITCHHandler handler;
        handler.initialize();
        handler.process(data.data(), data.size());
        benchmark::DoNotOptimize(handler.orders_added());
    }

    state.SetItemsProcessed(state.iterations() * num_messages);
}
BENCHMARK(BM_ITCH_HandlerWithOrderBook)->Arg(1000)->Arg(10000);

// Benchmark: Endianness conversion
static void BM_ITCH_Be64ToHost(benchmark::State& state) {
    uint8_t data[8] = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08};

    for (auto _ : state) {
        uint64_t result = be64_to_host(data);
        benchmark::DoNotOptimize(result);
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_ITCH_Be64ToHost);

// Benchmark: Message type dispatch
static void BM_ITCH_MessageDispatch(benchmark::State& state) {
    // Create a mix of message types
    MessageGenerator gen;
    gen.generate_add_order(1, true, 100, "AAPL    ", 1500000);
    gen.generate_order_delete(1);
    gen.generate_add_order(2, false, 50, "MSFT    ", 3500000);
    gen.generate_order_executed(2, 25);

    const auto& data = gen.data();

    Parser parser;
    int count = 0;
    parser.on_add_order([&](const AddOrder&) { ++count; });
    parser.on_order_delete([&](const OrderDelete&) { ++count; });
    parser.on_order_executed([&](const OrderExecuted&) { ++count; });

    for (auto _ : state) {
        count = 0;
        parser.parse_messages(data.data(), data.size());
        benchmark::DoNotOptimize(count);
    }

    state.SetItemsProcessed(state.iterations() * 4);  // 4 messages
}
BENCHMARK(BM_ITCH_MessageDispatch);

// Note: BENCHMARK_MAIN() is defined in bench_order_book.cpp
