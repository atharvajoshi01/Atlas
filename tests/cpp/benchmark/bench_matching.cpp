#include <benchmark/benchmark.h>
#include "atlas/matching/matching_engine.hpp"
#include "atlas/feed/ring_buffer.hpp"
#include "atlas/feed/market_data.hpp"

#include <random>

using namespace atlas;

// Benchmark order submission (no match)
static void BM_MatchingEngine_SubmitNoMatch(benchmark::State& state) {
    MatchingEngine engine;
    OrderId id = 1;
    std::mt19937_64 rng(42);

    for (auto _ : state) {
        // Alternate buy/sell at different prices (no crossing)
        if (id % 2 == 0) {
            benchmark::DoNotOptimize(
                engine.submit_order(id, to_price(99.0), 100, Side::Buy));
        } else {
            benchmark::DoNotOptimize(
                engine.submit_order(id, to_price(101.0), 100, Side::Sell));
        }
        id++;
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_MatchingEngine_SubmitNoMatch)->Range(1, 1 << 18);

// Benchmark order submission with matching
static void BM_MatchingEngine_SubmitWithMatch(benchmark::State& state) {
    MatchingEngine engine;
    OrderId id = 1;

    // Pre-populate with resting orders
    for (int i = 0; i < 1000; ++i) {
        engine.submit_order(id++, to_price(100.0), 100, Side::Sell);
    }

    for (auto _ : state) {
        // Submit crossing order
        auto result = engine.submit_order(id++, to_price(100.0), 10, Side::Buy);
        benchmark::DoNotOptimize(result);

        // Replenish liquidity periodically
        if (engine.get_order_book().best_ask_quantity() < 1000) {
            engine.submit_order(id++, to_price(100.0), 100, Side::Sell);
        }
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_MatchingEngine_SubmitWithMatch)->Range(1, 1 << 16);

// Benchmark cancel order
static void BM_MatchingEngine_CancelOrder(benchmark::State& state) {
    MatchingEngine engine;
    const int NUM_ORDERS = 50000;

    // Pre-populate
    for (int i = 1; i <= NUM_ORDERS; ++i) {
        Side side = (i % 2 == 0) ? Side::Buy : Side::Sell;
        Price price = side == Side::Buy ? to_price(99.0) : to_price(101.0);
        engine.submit_order(i, price, 100, side);
    }

    OrderId id = 1;
    for (auto _ : state) {
        benchmark::DoNotOptimize(engine.cancel_order(id));
        id = (id % NUM_ORDERS) + 1;

        // Re-add periodically
        if (engine.get_order_book().total_order_count() < NUM_ORDERS / 2) {
            for (int i = 0; i < 100; ++i) {
                OrderId new_id = NUM_ORDERS + id + i;
                Side side = (new_id % 2 == 0) ? Side::Buy : Side::Sell;
                Price price = side == Side::Buy ? to_price(99.0) : to_price(101.0);
                engine.submit_order(new_id, price, 100, side);
            }
        }
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_MatchingEngine_CancelOrder)->Range(1, 1 << 16);

// Benchmark modify order
static void BM_MatchingEngine_ModifyOrder(benchmark::State& state) {
    MatchingEngine engine;
    const int NUM_ORDERS = 10000;

    // Pre-populate
    for (int i = 1; i <= NUM_ORDERS; ++i) {
        engine.submit_order(i, to_price(100.0), 100, Side::Buy);
    }

    OrderId id = 1;
    std::mt19937_64 rng(42);
    std::uniform_int_distribution<Price> price_dist(to_price(99.0), to_price(100.0));

    for (auto _ : state) {
        Price new_price = price_dist(rng);
        auto result = engine.modify_order(id, new_price, 150);
        benchmark::DoNotOptimize(result);
        id = (id % NUM_ORDERS) + 1;
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_MatchingEngine_ModifyOrder)->Range(1, 1 << 14);

// Benchmark ring buffer operations
static void BM_RingBuffer_PushPop(benchmark::State& state) {
    SPSCRingBuffer<L2Message, 65536> buffer;
    L2Message msg{};
    msg.sequence = 1;

    for (auto _ : state) {
        buffer.try_push(msg);
        L2Message out;
        buffer.try_pop(out);
        benchmark::DoNotOptimize(out);
    }

    state.SetItemsProcessed(state.iterations() * 2);  // Push + pop
}
BENCHMARK(BM_RingBuffer_PushPop)->Range(1, 1 << 20);

// Benchmark ring buffer burst write
static void BM_RingBuffer_BurstWrite(benchmark::State& state) {
    const int BURST_SIZE = state.range(0);
    SPSCRingBuffer<L2Message, 65536> buffer;

    for (auto _ : state) {
        // Write burst
        for (int i = 0; i < BURST_SIZE; ++i) {
            L2Message msg{};
            msg.sequence = i;
            buffer.try_push(msg);
        }

        // Drain
        L2Message out;
        while (buffer.try_pop(out)) {}
    }

    state.SetItemsProcessed(state.iterations() * BURST_SIZE);
}
BENCHMARK(BM_RingBuffer_BurstWrite)->Arg(100)->Arg(1000)->Arg(10000);

// Benchmark realistic trading simulation
static void BM_MatchingEngine_Simulation(benchmark::State& state) {
    const double add_prob = 0.5;
    const double cancel_prob = 0.3;
    const double cross_prob = 0.2;

    std::mt19937_64 rng(42);
    std::uniform_real_distribution<double> uniform(0.0, 1.0);
    std::uniform_int_distribution<Price> price_dist(to_price(99.0), to_price(101.0));

    for (auto _ : state) {
        state.PauseTiming();
        MatchingEngine engine;
        std::vector<OrderId> active_bids, active_asks;
        active_bids.reserve(10000);
        active_asks.reserve(10000);
        OrderId next_id = 1;
        state.ResumeTiming();

        // Run 10000 operations per iteration
        for (int op = 0; op < 10000; ++op) {
            double roll = uniform(rng);

            if (roll < add_prob) {
                // Add limit order
                Price price = price_dist(rng);
                Side side = (next_id % 2 == 0) ? Side::Buy : Side::Sell;

                // Adjust price to not cross
                if (side == Side::Buy && engine.get_order_book().best_ask() != INVALID_PRICE) {
                    price = std::min(price, engine.get_order_book().best_ask() - 1);
                } else if (side == Side::Sell && engine.get_order_book().best_bid() != INVALID_PRICE) {
                    price = std::max(price, engine.get_order_book().best_bid() + 1);
                }

                auto result = engine.submit_order(next_id, price, 100, side);
                if (result.status == OrderStatus::New) {
                    if (side == Side::Buy) {
                        active_bids.push_back(next_id);
                    } else {
                        active_asks.push_back(next_id);
                    }
                }
                next_id++;

            } else if (roll < add_prob + cancel_prob) {
                // Cancel order
                auto& orders = (uniform(rng) < 0.5) ? active_bids : active_asks;
                if (!orders.empty()) {
                    std::uniform_int_distribution<size_t> idx_dist(0, orders.size() - 1);
                    size_t idx = idx_dist(rng);
                    engine.cancel_order(orders[idx]);
                    orders[idx] = orders.back();
                    orders.pop_back();
                }

            } else {
                // Crossing order (market-like)
                Side side = (uniform(rng) < 0.5) ? Side::Buy : Side::Sell;
                Price price = (side == Side::Buy) ?
                    engine.get_order_book().best_ask() :
                    engine.get_order_book().best_bid();

                if (price != INVALID_PRICE) {
                    engine.submit_order(next_id++, price, 50, side);
                }
            }
        }

        benchmark::DoNotOptimize(engine.total_trades());
    }

    state.SetItemsProcessed(state.iterations() * 10000);
}
BENCHMARK(BM_MatchingEngine_Simulation)->Unit(benchmark::kMillisecond);

// Benchmark L2 message processing latency
static void BM_L2Message_Parse(benchmark::State& state) {
    L2Message msg{};
    msg.timestamp = 1234567890;
    msg.symbol_id = 1;
    msg.price = to_price(100.0);
    msg.quantity = 100;
    msg.side = Side::Buy;
    msg.action = OrderAction::Add;
    msg.sequence = 1;

    for (auto _ : state) {
        // Simulate parsing by copying and accessing fields
        L2Message parsed = msg;
        benchmark::DoNotOptimize(parsed.price);
        benchmark::DoNotOptimize(parsed.quantity);
        benchmark::DoNotOptimize(parsed.side);
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_L2Message_Parse)->Range(1, 1 << 20);

// BENCHMARK_MAIN() is in bench_order_book.cpp
