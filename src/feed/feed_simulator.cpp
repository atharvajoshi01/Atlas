#include "atlas/feed/feed_handler.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <random>

namespace atlas {

// Feed simulator configuration
struct FeedSimulatorConfig {
    double base_price{100.0};           // Starting mid price
    double tick_size{0.01};             // Minimum price increment
    double daily_volatility{0.02};      // Annualized volatility
    double mean_spread_ticks{2.0};      // Average spread in ticks
    double order_arrival_rate{1000.0};  // Orders per second
    double cancel_ratio{0.4};           // Fraction of orders that get cancelled
    double market_order_ratio{0.05};    // Fraction that are market orders
    int depth_levels{20};               // Number of price levels to maintain
    double mean_order_size{100.0};      // Average order size
    double order_size_std{50.0};        // Std dev of order sizes
    uint32_t random_seed{42};           // For reproducibility
};

// Feed simulator for generating realistic market data
class FeedSimulator {
public:
    explicit FeedSimulator(FeedSimulatorConfig config = {})
        : config_(config)
        , rng_(config.random_seed)
        , mid_price_(config.base_price)
        , sequence_(1) {
        // Pre-compute volatility scaling
        // Daily vol to per-tick vol (assuming ~1000 messages/sec, ~23000 sec/day)
        tick_volatility_ = config_.daily_volatility / std::sqrt(23000.0 * 1000.0);
    }

    // Generate a single L2 update
    L2Message generate_update(Timestamp timestamp) {
        L2Message msg{};
        msg.timestamp = timestamp;
        msg.symbol_id = 1;
        msg.sequence = sequence_++;

        // Update mid price with random walk
        std::normal_distribution<double> price_move(0.0, tick_volatility_);
        mid_price_ += mid_price_ * price_move(rng_);
        mid_price_ = std::max(config_.tick_size, mid_price_);

        // Generate order characteristics
        std::uniform_real_distribution<double> uniform(0.0, 1.0);
        std::exponential_distribution<double> size_dist(1.0 / config_.mean_order_size);

        // Determine side (slight imbalance based on recent price moves)
        double buy_prob = 0.5 + (price_trend_ * 0.1);
        buy_prob = std::clamp(buy_prob, 0.3, 0.7);
        msg.side = uniform(rng_) < buy_prob ? Side::Buy : Side::Sell;

        // Determine action type
        double action_roll = uniform(rng_);
        if (action_roll < config_.cancel_ratio && active_orders_ > 10) {
            msg.action = OrderAction::Delete;
            msg.quantity = 0;
            --active_orders_;
        } else if (action_roll < config_.cancel_ratio + 0.1) {
            msg.action = OrderAction::Modify;
            msg.quantity = static_cast<Quantity>(
                std::max(1.0, size_dist(rng_)));
        } else {
            msg.action = OrderAction::Add;
            msg.quantity = static_cast<Quantity>(
                std::max(1.0, size_dist(rng_)));
            ++active_orders_;
        }

        // Generate price
        double spread = config_.mean_spread_ticks * config_.tick_size;
        std::exponential_distribution<double> depth_dist(2.0);

        if (msg.side == Side::Buy) {
            double offset = depth_dist(rng_) * config_.tick_size;
            msg.price = to_price(mid_price_ - spread / 2 - offset);
        } else {
            double offset = depth_dist(rng_) * config_.tick_size;
            msg.price = to_price(mid_price_ + spread / 2 + offset);
        }

        // Update trend estimate
        price_trend_ = 0.95 * price_trend_ +
                       0.05 * (msg.side == Side::Buy ? 1.0 : -1.0);

        return msg;
    }

    // Generate messages for a duration at the configured rate
    std::vector<L2Message> generate_batch(
        std::chrono::milliseconds duration,
        Timestamp start_time = 0
    ) {
        size_t num_messages = static_cast<size_t>(
            config_.order_arrival_rate *
            duration.count() / 1000.0
        );

        std::vector<L2Message> messages;
        messages.reserve(num_messages);

        // Distribute messages with Poisson timing
        std::exponential_distribution<double> inter_arrival(
            config_.order_arrival_rate
        );

        Timestamp current_time = start_time;
        for (size_t i = 0; i < num_messages; ++i) {
            current_time += static_cast<Timestamp>(
                inter_arrival(rng_) * 1e9  // Convert seconds to nanoseconds
            );
            messages.push_back(generate_update(current_time));
        }

        return messages;
    }

    // Generate and enqueue messages directly to feed handler
    size_t generate_to_handler(
        FeedHandler& handler,
        std::chrono::milliseconds duration,
        Timestamp start_time = 0
    ) {
        auto messages = generate_batch(duration, start_time);
        size_t enqueued = 0;

        for (const auto& msg : messages) {
            if (handler.enqueue_l2(msg)) {
                ++enqueued;
            }
        }

        return enqueued;
    }

    // Get current mid price
    [[nodiscard]] double mid_price() const noexcept {
        return mid_price_;
    }

    // Reset simulator state
    void reset() {
        mid_price_ = config_.base_price;
        sequence_ = 1;
        active_orders_ = 0;
        price_trend_ = 0.0;
        rng_.seed(config_.random_seed);
    }

    // Update configuration
    void set_volatility(double vol) {
        config_.daily_volatility = vol;
        tick_volatility_ = vol / std::sqrt(23000.0 * 1000.0);
    }

    void set_arrival_rate(double rate) {
        config_.order_arrival_rate = rate;
    }

    void set_spread(double spread_ticks) {
        config_.mean_spread_ticks = spread_ticks;
    }

private:
    FeedSimulatorConfig config_;
    std::mt19937_64 rng_;
    double mid_price_;
    double tick_volatility_;
    uint64_t sequence_;
    int active_orders_{0};
    double price_trend_{0.0};
};

}  // namespace atlas
