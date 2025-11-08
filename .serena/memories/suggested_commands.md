# Gaggle Development Commands

## Environment Setup
```bash
# Install all dependencies including dev tools
uv sync --dev

# Install only production dependencies  
uv sync
```

## Running the Application
```bash
# Show CLI help
uv run gaggle --help

# Run main application module
uv run python -m gaggle.main

# Run demonstration/examples
uv run python demo.py
uv run python simple_demo.py
uv run python cli_demo.py

# Initialize for a repository
uv run gaggle init https://github.com/your-org/your-repo --token $GITHUB_TOKEN

# Plan a sprint
uv run gaggle sprint plan --goal "Build a REST API for a todo application"

# Check team status
uv run gaggle team status

# View configuration
uv run gaggle config --show
```

## Code Quality & Linting
```bash
# Lint code (check for issues)
uv run ruff check

# Auto-fix linting issues
uv run ruff check --fix

# Format code
uv run black .

# Type checking
uv run mypy src/gaggle
```

## Testing
```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/unit/          # Unit tests only
uv run pytest tests/integration/   # Integration tests
uv run pytest -k "test_name"       # Run specific test
uv run pytest -m "unit"            # Run tests with specific marker
uv run pytest -m "fast"            # Run fast tests only

# Run with coverage
uv run pytest --cov=src/gaggle
uv run pytest --cov=src/gaggle --cov-report=html

# Test specific files
uv run pytest test_simple.py
uv run pytest test_phase1_communication.py
uv run pytest test_productionized_features.py
```

## Pre-commit Hooks
```bash
# Install git hooks
uv run pre-commit install

# Run all hooks manually
uv run pre-commit run --all-files
```

## Development Utilities
```bash
# Test basic functionality
uv run python simple_test.py

# Run validation summary
uv run python validation_summary.py
```

## System Utilities (macOS/Darwin)
```bash
# File operations
ls -la                    # List files with details
find . -name "*.py"       # Find Python files
grep -r "pattern" src/    # Search for patterns
cd src/gaggle            # Change directory

# Git operations
git status               # Check repository status
git diff                 # View changes
git add .                # Stage changes
git commit -m "message"  # Commit changes
git push                 # Push to remote

# Process management
ps aux | grep python     # Find Python processes
kill -9 <pid>           # Kill specific process
```

## Environment Variables
```bash
# Required for real functionality
export GITHUB_TOKEN=ghp_your_token_here
export GITHUB_REPO=your-repo-name

# LLM Provider (choose one)
export ANTHROPIC_API_KEY=your_key_here
# OR
export AWS_PROFILE=your_aws_profile

# Optional configuration
export GAGGLE_LOG_LEVEL=INFO
export GAGGLE_DEBUG_MODE=false
export GAGGLE_DRY_RUN=false
```