.PHONY: install dev clean build run

# Default target
all: install

# Install from source
install:
	pip install -e .

# Set up development environment
dev:
	pip install -e ".[dev]"
	pip install -r requirements.txt

# Run the application
run:
	python -m appimagemanager

# Build DEB package using the provided script
build:
	chmod +x build_and_install.sh
	./build_and_install.sh

# Clean up build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ deb_pkg/ *.deb
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete

# Build distribution packages
dist:
	python -m build

# Help text
help:
	@echo "Available targets:"
	@echo "  make install  - Install the package"
	@echo "  make dev      - Set up development environment"
	@echo "  make run      - Run the application"
	@echo "  make build    - Build the DEB package"
	@echo "  make clean    - Clean up build artifacts"
	@echo "  make dist     - Build distribution packages" 