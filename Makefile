.PHONY: all build test bench clean install lint format help

# Default target
all: build

# Build C++ components
build:
	@mkdir -p build
	@cd build && cmake -DCMAKE_BUILD_TYPE=Release \
		-DATLAS_BUILD_TESTS=ON \
		-DATLAS_BUILD_BENCHMARKS=ON \
		-DATLAS_BUILD_PYTHON=ON \
		..
	@cd build && make -j$$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)

# Build debug version
build-debug:
	@mkdir -p build-debug
	@cd build-debug && cmake -DCMAKE_BUILD_TYPE=Debug \
		-DATLAS_BUILD_TESTS=ON \
		-DATLAS_ENABLE_SANITIZERS=ON \
		..
	@cd build-debug && make -j$$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)

# Run C++ tests
test-cpp:
	@cd build && ctest --verbose --output-on-failure

# Run C++ benchmarks
bench:
	@./build/atlas_benchmarks --benchmark_format=console

# Install Python package
install:
	pip install -e ".[all]"

# Run Python tests
test-python:
	pytest atlas/ -v --cov=atlas

# Run all tests
test: test-cpp test-python

# Lint Python code
lint:
	ruff check atlas/
	mypy atlas/ --ignore-missing-imports

# Format Python code
format:
	ruff format atlas/
	ruff check --fix atlas/

# Clean build artifacts
clean:
	rm -rf build build-debug
	rm -rf atlas/*.so atlas/__pycache__
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Run Streamlit dashboard
dashboard:
	streamlit run dashboard/app.py

# Generate documentation
docs:
	@echo "Documentation generation not yet configured"

# Show help
help:
	@echo "Atlas Makefile Commands:"
	@echo "  make build       - Build C++ components (Release)"
	@echo "  make build-debug - Build C++ components (Debug with sanitizers)"
	@echo "  make test-cpp    - Run C++ tests"
	@echo "  make test-python - Run Python tests"
	@echo "  make test        - Run all tests"
	@echo "  make bench       - Run C++ benchmarks"
	@echo "  make install     - Install Python package"
	@echo "  make lint        - Lint Python code"
	@echo "  make format      - Format Python code"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make dashboard   - Run Streamlit dashboard"
	@echo "  make help        - Show this help"
