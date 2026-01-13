#include <benchmark/benchmark.h>
#include "atlas/core/order_book.hpp"
#include "atlas/core/types.hpp"
#include "atlas/memory/pool_allocator.hpp"

#include <random>

using namespace atlas;

// Benchmark order addition
static void BM_OrderBook_AddOrder(benchmark::State& state) {
    OrderBook book;
    OrderId id = 1;
    std::mt19937_64 rng(42);
    std::uniform_int_distribution<Price> price_dist(to_price(99.0), to_price(101.0));
    std::uniform_int_distribution<Quantity> qty_dist(1, 1000);

    for (auto _ : state) {
        Price price = price_dist(rng);
        Quantity qty = qty_dist(rng);
        Side side = (id % 2 == 0) ? Side::Buy : Side::Sell;

        benchmark::DoNotOptimize(book.add_order(id++, price, qty, side));
    }

    state.SetItemsProcessed(state.iterations());
    state.counters["orders"] = book.total_order_count();
}
BENCHMARK(BM_OrderBook_AddOrder)->Range(1, 1 << 20);

// Benchmark order cancellation
static void BM_OrderBook_CancelOrder(benchmark::State& state) {
    OrderBook book;
    const int NUM_ORDERS = 100000;

    // Pre-populate book
    for (int i = 1; i <= NUM_ORDERS; ++i) {
        Price price = to_price(100.0) + (i % 100);
        Side side = (i % 2 == 0) ? Side::Buy : Side::Sell;
        book.add_order(i, price, 100, side);
    }

    OrderId id = 1;
    for (auto _ : state) {
        benchmark::DoNotOptimize(book.cancel_order(id));
        id = (id % NUM_ORDERS) + 1;

        // Re-add if cancelled
        if (book.get_order(id) == nullptr) {
            Price price = to_price(100.0) + (id % 100);
            Side side = (id % 2 == 0) ? Side::Buy : Side::Sell;
            book.add_order(id, price, 100, side);
        }
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_OrderBook_CancelOrder)->Range(1, 1 << 18);

// Benchmark BBO access
static void BM_OrderBook_GetBBO(benchmark::State& state) {
    OrderBook book;

    // Populate book
    for (int i = 1; i <= 10000; ++i) {
        Price price = to_price(100.0) + (i % 100);
        Side side = (i % 2 == 0) ? Side::Buy : Side::Sell;
        book.add_order(i, price, 100, side);
    }

    for (auto _ : state) {
        BBO bbo = book.get_bbo();
        benchmark::DoNotOptimize(bbo);
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_OrderBook_GetBBO)->Range(1, 1 << 20);

// Benchmark best bid access
static void BM_OrderBook_BestBid(benchmark::State& state) {
    OrderBook book;

    for (int i = 1; i <= 10000; ++i) {
        Price price = to_price(100.0) - (i % 100);
        book.add_order(i, price, 100, Side::Buy);
    }

    for (auto _ : state) {
        Price bid = book.best_bid();
        benchmark::DoNotOptimize(bid);
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_OrderBook_BestBid)->Range(1, 1 << 20);

// Benchmark depth retrieval
static void BM_OrderBook_GetDepth(benchmark::State& state) {
    const int depth_levels = state.range(0);
    OrderBook book;

    // Populate book with many levels
    for (int i = 1; i <= 50000; ++i) {
        Price price = to_price(100.0) + (i % 500) - 250;
        Side side = (i % 2 == 0) ? Side::Buy : Side::Sell;
        book.add_order(i, price, 100, side);
    }

    std::vector<DepthLevel> bids, asks;
    bids.reserve(depth_levels);
    asks.reserve(depth_levels);

    for (auto _ : state) {
        book.get_depth(bids, asks, depth_levels);
        benchmark::DoNotOptimize(bids.data());
        benchmark::DoNotOptimize(asks.data());
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_OrderBook_GetDepth)->Arg(5)->Arg(10)->Arg(20)->Arg(50);

// Benchmark mid price calculation
static void BM_OrderBook_MidPrice(benchmark::State& state) {
    OrderBook book;

    book.add_order(1, to_price(100.0), 1000, Side::Buy);
    book.add_order(2, to_price(100.02), 1000, Side::Sell);

    for (auto _ : state) {
        Price mid = book.mid_price();
        benchmark::DoNotOptimize(mid);
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_OrderBook_MidPrice)->Range(1, 1 << 20);

// Benchmark VWAP calculation
static void BM_OrderBook_VWAP(benchmark::State& state) {
    OrderBook book;

    // Build realistic book
    for (int i = 1; i <= 1000; ++i) {
        Price bid_price = to_price(100.0 - (i - 1) * 0.01);
        Price ask_price = to_price(100.01 + (i - 1) * 0.01);
        book.add_order(i * 2 - 1, bid_price, 100 * i, Side::Buy);
        book.add_order(i * 2, ask_price, 100 * i, Side::Sell);
    }

    Quantity target = 5000;

    for (auto _ : state) {
        auto vwap = book.calculate_vwap(Side::Sell, target);
        benchmark::DoNotOptimize(vwap);
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_OrderBook_VWAP)->Range(1, 1 << 16);

// Benchmark memory pool allocation
static void BM_PoolAllocator_Allocate(benchmark::State& state) {
    PoolAllocator<Order, 1000000> pool;

    for (auto _ : state) {
        Order* order = pool.allocate();
        benchmark::DoNotOptimize(order);
        pool.deallocate(order);
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_PoolAllocator_Allocate)->Range(1, 1 << 20);

// Benchmark atomic pool allocation
static void BM_AtomicPoolAllocator_Allocate(benchmark::State& state) {
    AtomicPoolAllocator<Order, 1000000> pool;

    for (auto _ : state) {
        Order* order = pool.allocate();
        benchmark::DoNotOptimize(order);
        pool.deallocate(order);
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_AtomicPoolAllocator_Allocate)->Range(1, 1 << 20);

// Compare with standard new/delete
static void BM_StandardAlloc(benchmark::State& state) {
    for (auto _ : state) {
        Order* order = new Order();
        benchmark::DoNotOptimize(order);
        delete order;
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_StandardAlloc)->Range(1, 1 << 20);

// Benchmark realistic workload: mixed adds and cancels
static void BM_OrderBook_MixedWorkload(benchmark::State& state) {
    OrderBook book;
    std::mt19937_64 rng(42);
    std::uniform_real_distribution<double> uniform(0.0, 1.0);
    std::uniform_int_distribution<Price> price_dist(to_price(99.0), to_price(101.0));

    OrderId next_id = 1;
    std::vector<OrderId> active_orders;
    active_orders.reserve(10000);

    for (auto _ : state) {
        double roll = uniform(rng);

        if (roll < 0.6 || active_orders.empty()) {
            // Add order (60% of the time)
            Price price = price_dist(rng);
            Side side = (next_id % 2 == 0) ? Side::Buy : Side::Sell;
            Order* order = book.add_order(next_id, price, 100, side);
            if (order) {
                active_orders.push_back(next_id);
            }
            next_id++;
        } else {
            // Cancel order (40% of the time)
            std::uniform_int_distribution<size_t> idx_dist(0, active_orders.size() - 1);
            size_t idx = idx_dist(rng);
            OrderId id = active_orders[idx];

            book.cancel_order(id);

            // Remove from active list
            active_orders[idx] = active_orders.back();
            active_orders.pop_back();
        }
    }

    state.SetItemsProcessed(state.iterations());
    state.counters["final_orders"] = book.total_order_count();
}
BENCHMARK(BM_OrderBook_MixedWorkload)->Range(1, 1 << 18);

BENCHMARK_MAIN();
