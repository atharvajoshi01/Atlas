#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include "atlas/core/types.hpp"
#include "atlas/core/order.hpp"
#include "atlas/core/order_book.hpp"
#include "atlas/matching/matching_engine.hpp"
#include "atlas/feed/feed_handler.hpp"
#include "atlas/feed/market_data.hpp"
#include "atlas/feed/ring_buffer.hpp"

namespace py = pybind11;

using namespace atlas;

PYBIND11_MODULE(_atlas, m) {
    m.doc() = "Atlas: Low-Latency Order Book Engine";

    // =========================================================================
    // Core Types
    // =========================================================================

    py::enum_<Side>(m, "Side")
        .value("Buy", Side::Buy)
        .value("Sell", Side::Sell)
        .export_values();

    py::enum_<OrderType>(m, "OrderType")
        .value("Limit", OrderType::Limit)
        .value("Market", OrderType::Market)
        .value("IOC", OrderType::IOC)
        .value("FOK", OrderType::FOK)
        .export_values();

    py::enum_<OrderStatus>(m, "OrderStatus")
        .value("New", OrderStatus::New)
        .value("PartiallyFilled", OrderStatus::PartiallyFilled)
        .value("Filled", OrderStatus::Filled)
        .value("Cancelled", OrderStatus::Cancelled)
        .value("Rejected", OrderStatus::Rejected)
        .export_values();

    // Price conversion utilities
    m.def("to_price", &to_price, "Convert double to fixed-point price",
          py::arg("value"));
    m.def("from_price", &from_price, "Convert fixed-point price to double",
          py::arg("price"));

    m.attr("PRICE_MULTIPLIER") = PRICE_MULTIPLIER;
    m.attr("INVALID_PRICE") = INVALID_PRICE;
    m.attr("INVALID_ORDER_ID") = INVALID_ORDER_ID;

    // =========================================================================
    // Order
    // =========================================================================

    py::class_<Order>(m, "Order")
        .def(py::init<>())
        .def(py::init<OrderId, Price, Quantity, Side, OrderType, Timestamp>(),
             py::arg("id"), py::arg("price"), py::arg("quantity"),
             py::arg("side"), py::arg("type") = OrderType::Limit,
             py::arg("timestamp") = 0)
        .def_readwrite("id", &Order::id)
        .def_readwrite("price", &Order::price)
        .def_readwrite("quantity", &Order::quantity)
        .def_readwrite("filled_quantity", &Order::filled_quantity)
        .def_readwrite("timestamp", &Order::timestamp)
        .def_readwrite("side", &Order::side)
        .def_readwrite("type", &Order::type)
        .def_readwrite("status", &Order::status)
        .def_property_readonly("remaining", &Order::remaining)
        .def_property_readonly("is_filled", &Order::is_filled)
        .def_property_readonly("is_active", &Order::is_active)
        .def_property_readonly("is_buy", &Order::is_buy)
        .def_property_readonly("is_sell", &Order::is_sell)
        .def("fill", &Order::fill, py::arg("quantity"))
        .def("cancel", &Order::cancel)
        .def("__repr__", [](const Order& o) {
            return "<Order id=" + std::to_string(o.id) +
                   " price=" + std::to_string(from_price(o.price)) +
                   " qty=" + std::to_string(o.quantity) +
                   " side=" + std::string(side_to_string(o.side)) +
                   " status=" + std::string(order_status_to_string(o.status)) + ">";
        });

    // =========================================================================
    // Trade
    // =========================================================================

    py::class_<Trade>(m, "Trade")
        .def(py::init<>())
        .def_readwrite("trade_id", &Trade::trade_id)
        .def_readwrite("buyer_order_id", &Trade::buyer_order_id)
        .def_readwrite("seller_order_id", &Trade::seller_order_id)
        .def_readwrite("price", &Trade::price)
        .def_readwrite("quantity", &Trade::quantity)
        .def_readwrite("timestamp", &Trade::timestamp)
        .def_readwrite("aggressor_side", &Trade::aggressor_side)
        .def("__repr__", [](const Trade& t) {
            return "<Trade id=" + std::to_string(t.trade_id) +
                   " price=" + std::to_string(from_price(t.price)) +
                   " qty=" + std::to_string(t.quantity) + ">";
        });

    // =========================================================================
    // BBO
    // =========================================================================

    py::class_<BBO>(m, "BBO")
        .def(py::init<>())
        .def_readwrite("bid_price", &BBO::bid_price)
        .def_readwrite("bid_quantity", &BBO::bid_quantity)
        .def_readwrite("ask_price", &BBO::ask_price)
        .def_readwrite("ask_quantity", &BBO::ask_quantity)
        .def_property_readonly("has_bid", &BBO::has_bid)
        .def_property_readonly("has_ask", &BBO::has_ask)
        .def_property_readonly("has_both", &BBO::has_both)
        .def_property_readonly("spread", &BBO::spread)
        .def_property_readonly("mid_price", &BBO::mid_price)
        .def("__repr__", [](const BBO& bbo) {
            std::string repr = "<BBO ";
            if (bbo.has_bid()) {
                repr += "bid=" + std::to_string(from_price(bbo.bid_price)) +
                        "x" + std::to_string(bbo.bid_quantity);
            }
            if (bbo.has_both()) repr += " ";
            if (bbo.has_ask()) {
                repr += "ask=" + std::to_string(from_price(bbo.ask_price)) +
                        "x" + std::to_string(bbo.ask_quantity);
            }
            return repr + ">";
        });

    // =========================================================================
    // DepthLevel
    // =========================================================================

    py::class_<DepthLevel>(m, "DepthLevel")
        .def(py::init<>())
        .def_readwrite("price", &DepthLevel::price)
        .def_readwrite("quantity", &DepthLevel::quantity)
        .def_readwrite("order_count", &DepthLevel::order_count);

    // =========================================================================
    // ExecutionResult
    // =========================================================================

    py::class_<ExecutionResult>(m, "ExecutionResult")
        .def(py::init<>())
        .def_readwrite("order_id", &ExecutionResult::order_id)
        .def_readwrite("status", &ExecutionResult::status)
        .def_readwrite("filled_quantity", &ExecutionResult::filled_quantity)
        .def_readwrite("avg_fill_price", &ExecutionResult::avg_fill_price)
        .def_readwrite("trade_count", &ExecutionResult::trade_count)
        .def_property_readonly("is_accepted", &ExecutionResult::is_accepted)
        .def_property_readonly("is_filled", &ExecutionResult::is_filled);

    // =========================================================================
    // OrderBook
    // =========================================================================

    py::class_<OrderBook>(m, "OrderBook")
        .def(py::init<size_t>(), py::arg("pool_size") = 100000)

        // Core operations
        .def("add_order", &OrderBook::add_order,
             py::arg("id"), py::arg("price"), py::arg("quantity"),
             py::arg("side"), py::arg("type") = OrderType::Limit,
             py::arg("timestamp") = 0,
             py::return_value_policy::reference,
             py::call_guard<py::gil_scoped_release>())

        .def("cancel_order", &OrderBook::cancel_order,
             py::arg("id"),
             py::call_guard<py::gil_scoped_release>())

        .def("modify_order", &OrderBook::modify_order,
             py::arg("id"), py::arg("new_price"), py::arg("new_quantity"),
             py::return_value_policy::reference,
             py::call_guard<py::gil_scoped_release>())

        .def("get_order", &OrderBook::get_order,
             py::arg("id"),
             py::return_value_policy::reference)

        // BBO
        .def("get_bbo", &OrderBook::get_bbo)
        .def("best_bid", &OrderBook::best_bid)
        .def("best_ask", &OrderBook::best_ask)
        .def("best_bid_quantity", &OrderBook::best_bid_quantity)
        .def("best_ask_quantity", &OrderBook::best_ask_quantity)
        .def("mid_price", &OrderBook::mid_price)
        .def("spread", &OrderBook::spread)

        // Depth - returns NumPy array for efficiency
        .def("get_depth_array", [](const OrderBook& book, int levels) {
            std::vector<DepthLevel> bids, asks;
            book.get_depth(bids, asks, levels);

            // Create NumPy array with shape (levels, 4)
            // Columns: bid_price, bid_size, ask_price, ask_size
            py::array_t<double> result({levels, 4});
            auto buf = result.mutable_unchecked<2>();

            for (int i = 0; i < levels; ++i) {
                if (i < static_cast<int>(bids.size())) {
                    buf(i, 0) = from_price(bids[i].price);
                    buf(i, 1) = static_cast<double>(bids[i].quantity);
                } else {
                    buf(i, 0) = 0.0;
                    buf(i, 1) = 0.0;
                }
                if (i < static_cast<int>(asks.size())) {
                    buf(i, 2) = from_price(asks[i].price);
                    buf(i, 3) = static_cast<double>(asks[i].quantity);
                } else {
                    buf(i, 2) = 0.0;
                    buf(i, 3) = 0.0;
                }
            }

            return result;
        }, py::arg("levels") = 10,
           "Get order book depth as NumPy array (levels x 4: bid_price, bid_size, ask_price, ask_size)")

        .def("get_bid_depth", [](const OrderBook& book, size_t max_levels) {
            std::vector<DepthLevel> levels;
            book.get_bid_depth(levels, max_levels);
            return levels;
        }, py::arg("max_levels") = 10)

        .def("get_ask_depth", [](const OrderBook& book, size_t max_levels) {
            std::vector<DepthLevel> levels;
            book.get_ask_depth(levels, max_levels);
            return levels;
        }, py::arg("max_levels") = 10)

        // Volume
        .def("total_bid_volume", &OrderBook::total_bid_volume)
        .def("total_ask_volume", &OrderBook::total_ask_volume)
        .def("bid_level_count", &OrderBook::bid_level_count)
        .def("ask_level_count", &OrderBook::ask_level_count)
        .def("total_order_count", &OrderBook::total_order_count)

        // VWAP
        .def("calculate_vwap", [](const OrderBook& book, Side side, Quantity qty) {
            auto result = book.calculate_vwap(side, qty);
            if (result) {
                return py::cast(from_price(*result));
            }
            return py::cast(py::none());
        }, py::arg("side"), py::arg("quantity"))

        // Utilities
        .def("would_cross", &OrderBook::would_cross,
             py::arg("price"), py::arg("side"))
        .def("clear", &OrderBook::clear)
        .def("empty", &OrderBook::empty)

        // Callbacks
        .def("set_trade_callback", [](OrderBook& book, py::function callback) {
            book.set_trade_callback([callback](const Trade& trade) {
                py::gil_scoped_acquire acquire;
                callback(trade);
            });
        })

        .def("set_book_update_callback", [](OrderBook& book, py::function callback) {
            book.set_book_update_callback([callback](const BookUpdate& update) {
                py::gil_scoped_acquire acquire;
                callback(from_price(update.price), update.quantity,
                        update.side == Side::Buy ? "buy" : "sell");
            });
        })

        .def("__repr__", [](const OrderBook& book) {
            BBO bbo = book.get_bbo();
            std::string repr = "<OrderBook orders=" + std::to_string(book.total_order_count());
            if (bbo.has_both()) {
                repr += " bid=" + std::to_string(from_price(bbo.bid_price)) +
                        " ask=" + std::to_string(from_price(bbo.ask_price));
            }
            return repr + ">";
        });

    // =========================================================================
    // MatchingEngine
    // =========================================================================

    py::class_<MatchingEngine>(m, "MatchingEngine")
        .def(py::init<>())
        .def(py::init<MatchingEngineConfig>())

        .def("submit_order", &MatchingEngine::submit_order,
             py::arg("id"), py::arg("price"), py::arg("quantity"),
             py::arg("side"), py::arg("type") = OrderType::Limit,
             py::arg("timestamp") = 0, py::arg("participant_id") = 0,
             py::call_guard<py::gil_scoped_release>())

        .def("submit_market_order", &MatchingEngine::submit_market_order,
             py::arg("id"), py::arg("quantity"), py::arg("side"),
             py::arg("timestamp") = 0, py::arg("participant_id") = 0,
             py::call_guard<py::gil_scoped_release>())

        .def("cancel_order", &MatchingEngine::cancel_order,
             py::arg("id"),
             py::call_guard<py::gil_scoped_release>())

        .def("modify_order", &MatchingEngine::modify_order,
             py::arg("id"), py::arg("new_price"), py::arg("new_quantity"),
             py::call_guard<py::gil_scoped_release>())

        .def("get_order_book", py::overload_cast<>(&MatchingEngine::get_order_book),
             py::return_value_policy::reference)

        .def("get_trades", &MatchingEngine::get_trades)
        .def("peek_trades", &MatchingEngine::peek_trades,
             py::return_value_policy::reference)

        .def("set_trade_callback", [](MatchingEngine& engine, py::function callback) {
            engine.set_trade_callback([callback](const Trade& trade) {
                py::gil_scoped_acquire acquire;
                callback(trade);
            });
        })

        .def("total_trades", &MatchingEngine::total_trades)
        .def("total_volume", &MatchingEngine::total_volume)
        .def("total_orders_submitted", &MatchingEngine::total_orders_submitted)
        .def("total_orders_cancelled", &MatchingEngine::total_orders_cancelled)
        .def("reset", &MatchingEngine::reset);

    // =========================================================================
    // MatchingEngineConfig
    // =========================================================================

    py::class_<MatchingEngineConfig>(m, "MatchingEngineConfig")
        .def(py::init<>())
        .def_readwrite("self_trade_prevention", &MatchingEngineConfig::self_trade_prevention)
        .def_readwrite("allow_market_orders", &MatchingEngineConfig::allow_market_orders)
        .def_readwrite("allow_ioc_orders", &MatchingEngineConfig::allow_ioc_orders)
        .def_readwrite("allow_fok_orders", &MatchingEngineConfig::allow_fok_orders)
        .def_readwrite("max_order_quantity", &MatchingEngineConfig::max_order_quantity);

    // =========================================================================
    // L2Message
    // =========================================================================

    py::class_<L2Message>(m, "L2Message")
        .def(py::init<>())
        .def_readwrite("timestamp", &L2Message::timestamp)
        .def_readwrite("symbol_id", &L2Message::symbol_id)
        .def_readwrite("price", &L2Message::price)
        .def_readwrite("quantity", &L2Message::quantity)
        .def_readwrite("side", &L2Message::side)
        .def_readwrite("sequence", &L2Message::sequence);

    // =========================================================================
    // FeedStats
    // =========================================================================

    py::class_<FeedStats>(m, "FeedStats")
        .def(py::init<>())
        .def_readonly("messages_received", &FeedStats::messages_received)
        .def_readonly("messages_processed", &FeedStats::messages_processed)
        .def_readonly("sequence_gaps", &FeedStats::sequence_gaps)
        .def_readonly("parse_errors", &FeedStats::parse_errors)
        .def_readonly("buffer_overflows", &FeedStats::buffer_overflows)
        .def_readonly("last_sequence", &FeedStats::last_sequence);

    // =========================================================================
    // FeedHandler
    // =========================================================================

    py::class_<FeedHandler>(m, "FeedHandler")
        .def(py::init<>())
        .def("start", &FeedHandler::start)
        .def("stop", &FeedHandler::stop)
        .def("is_running", &FeedHandler::is_running)
        .def("enqueue_l2", &FeedHandler::enqueue_l2)
        .def("process_messages", &FeedHandler::process_messages,
             py::arg("max_messages") = 0)
        .def("get_order_book",
             py::overload_cast<SymbolId>(&FeedHandler::get_order_book),
             py::return_value_policy::reference)
        .def("create_order_book", &FeedHandler::create_order_book,
             py::return_value_policy::reference)
        .def("get_stats", &FeedHandler::get_stats,
             py::return_value_policy::reference)
        .def("reset_stats", &FeedHandler::reset_stats);

    // =========================================================================
    // Version info
    // =========================================================================

    m.attr("__version__") = "0.1.0";
    m.attr("__author__") = "Atlas Team";
}
