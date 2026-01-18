cmake_minimum_required(VERSION 3.20)
project(Atlas VERSION 0.1.0 LANGUAGES CXX)

# C++20 required
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Export compile commands for IDE support
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Options
option(ATLAS_BUILD_TESTS "Build tests" ON)
option(ATLAS_BUILD_BENCHMARKS "Build benchmarks" ON)
option(ATLAS_BUILD_PYTHON "Build Python bindings" ON)
option(ATLAS_ENABLE_SANITIZERS "Enable sanitizers in debug" OFF)

# Option to disable march=native (for CI)
option(ATLAS_NATIVE_ARCH "Enable -march=native optimization" ON)

# Compiler flags
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wpedantic")
    if(ATLAS_NATIVE_ARCH)
        set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -DNDEBUG -flto")
    else()
        set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
    endif()
    set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")

    if(ATLAS_ENABLE_SANITIZERS)
        set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -fsanitize=address,undefined")
        set(CMAKE_EXE_LINKER_FLAGS_DEBUG "${CMAKE_EXE_LINKER_FLAGS_DEBUG} -fsanitize=address,undefined")
    endif()
endif()

# Find packages
find_package(Threads REQUIRED)

if(ATLAS_BUILD_PYTHON)
    find_package(Python3 COMPONENTS Interpreter Development NumPy)
    find_package(pybind11 CONFIG)
    if(NOT pybind11_FOUND)
        message(STATUS "pybind11 not found via config, trying subdirectory or FetchContent")
        include(FetchContent)
        FetchContent_Declare(
            pybind11
            GIT_REPOSITORY https://github.com/pybind/pybind11.git
            GIT_TAG v2.11.1
        )
        FetchContent_MakeAvailable(pybind11)
    endif()
endif()

if(ATLAS_BUILD_TESTS)
    include(FetchContent)
    FetchContent_Declare(
        googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG v1.14.0
    )
    FetchContent_MakeAvailable(googletest)
    enable_testing()
endif()

if(ATLAS_BUILD_BENCHMARKS)
    find_package(benchmark CONFIG)
    if(NOT benchmark_FOUND)
        include(FetchContent)
        FetchContent_Declare(
            benchmark
            GIT_REPOSITORY https://github.com/google/benchmark.git
            GIT_TAG v1.8.3
        )
        set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
        FetchContent_MakeAvailable(benchmark)
    endif()
endif()

# Include directories
include_directories(${PROJECT_SOURCE_DIR}/include)

# Core library
add_library(atlas_core STATIC
    src/core/order_book.cpp
    src/core/price_level.cpp
    src/memory/pool_allocator.cpp
    src/matching/matching_engine.cpp
    src/feed/feed_handler.cpp
    src/feed/feed_simulator.cpp
)

target_include_directories(atlas_core PUBLIC
    $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries(atlas_core PUBLIC Threads::Threads)

# Python bindings
if(ATLAS_BUILD_PYTHON AND pybind11_FOUND)
    pybind11_add_module(_atlas src/bindings/python_bindings.cpp)
    target_link_libraries(_atlas PRIVATE atlas_core)

    # Copy to atlas package directory
    add_custom_command(TARGET _atlas POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy
            $<TARGET_FILE:_atlas>
            ${PROJECT_SOURCE_DIR}/atlas/
    )
endif()

# Tests
if(ATLAS_BUILD_TESTS)
    add_executable(atlas_tests
        tests/cpp/test_order_book.cpp
        tests/cpp/test_matching_engine.cpp
        tests/cpp/test_memory_pool.cpp
        tests/cpp/test_ring_buffer.cpp
    )
    target_link_libraries(atlas_tests PRIVATE atlas_core GTest::gtest_main)

    include(GoogleTest)
    gtest_discover_tests(atlas_tests)
endif()

# Benchmarks
if(ATLAS_BUILD_BENCHMARKS)
    add_executable(atlas_benchmarks
        tests/cpp/benchmark/bench_order_book.cpp
        tests/cpp/benchmark/bench_matching.cpp
    )
    target_link_libraries(atlas_benchmarks PRIVATE atlas_core benchmark::benchmark)
endif()

# Installation
install(TARGETS atlas_core
    EXPORT AtlasTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
    INCLUDES DESTINATION include
)

install(DIRECTORY include/atlas
    DESTINATION include
)
