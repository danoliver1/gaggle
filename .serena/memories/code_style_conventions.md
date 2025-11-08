# Gaggle Code Style & Conventions

## Language & Version
- **Python 3.10+** required (supports modern type hints with union operator `|`)
- **Modern type hints**: Use `str | None` instead of `Optional[str]`
- **Async-first**: Prefer async/await patterns for agent coordination

## Code Formatting & Linting
- **Line length**: 88 characters (configured in pyproject.toml)
- **Quote style**: Double quotes (`"`) preferred
- **Import sorting**: isort with `gaggle` as known first-party
- **Linting**: ruff with comprehensive rule set (E, W, F, I, N, UP, B, C4, SIM, A, T20)
- **Formatting**: black for consistent code formatting
- **Type checking**: mypy with strict mode enabled

## Project Structure Conventions
```
src/gaggle/
├── core/           # Sprint orchestration, team management, backlog, metrics
├── agents/         # Agent implementations by layer (coordination/architecture/implementation/qa)
├── workflows/      # Sprint workflow implementations (planning/execution/review/retrospective)
├── integrations/   # External services (GitHub, Strands, LLM providers)
├── models/         # Pydantic data models for sprints, stories, tasks, team
├── tools/          # Agent tools for GitHub, code generation, testing, reviews
├── config/         # Settings management and model configurations
└── utils/          # Shared utilities (logging, token counting, cost calculation)
```

## Model & Data Conventions
- **Pydantic v2**: All data models use Pydantic v2 syntax
- **Field validation**: Use `@field_validator` (not deprecated `@validator`)
- **Type hints**: Comprehensive type annotations on all functions/methods
- **Docstrings**: Google-style docstrings for classes and important methods
- **Business logic**: Rich domain models with validation and business rules

## Agent Architecture Patterns
- **Base class inheritance**: All agents inherit from `BaseAgent`
- **Context sharing**: Agents use shared `AgentContext` for coordination
- **Role-based model assignment**: Strategic model tier usage (Haiku/Sonnet/Opus)
- **Async methods**: All agent operations are async for parallelization
- **State machines**: Context-aware agent states with formal transitions

## Naming Conventions
- **Classes**: PascalCase (e.g., `ProductOwner`, `SprintModel`)
- **Functions/methods**: snake_case (e.g., `analyze_requirements`, `create_user_stories`)
- **Variables**: snake_case (e.g., `sprint_goal`, `user_stories`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_SPRINT_DURATION`)
- **Files/modules**: snake_case (e.g., `product_owner.py`, `sprint_execution.py`)

## Testing Conventions
- **Test files**: `test_*.py` pattern
- **Test classes**: `Test*` pattern
- **Test functions**: `test_*` pattern
- **Async tests**: Use `pytest-asyncio` with `asyncio_mode = auto`
- **Test markers**: Comprehensive categorization (unit, integration, end_to_end, fast, slow, etc.)
- **Coverage**: 80% minimum coverage requirement
- **Mocking**: Prefer mocking external dependencies (LLM calls, GitHub API)

## Error Handling
- **Validation errors**: Pydantic validation with clear error messages
- **Business rule validation**: Custom validators with descriptive messages
- **Exception handling**: Graceful error handling with structured logging
- **Type safety**: Strict mypy configuration to catch type errors

## Documentation Standards
- **Module docstrings**: Brief description of module purpose
- **Class docstrings**: Explain class responsibility and usage
- **Method docstrings**: Document parameters, return values, and side effects
- **Complex logic**: Inline comments for business logic and algorithms
- **API documentation**: Type hints serve as API documentation

## Import Organization
```python
# Standard library imports
import asyncio
from datetime import date, datetime
from typing import Any

# Third-party imports
import typer
from pydantic import BaseModel, Field, field_validator
from rich.console import Console

# Local imports (absolute from src/gaggle)
from .models.sprint import Sprint
from .agents.base import BaseAgent
from .utils.logging import get_logger
```

## Configuration Management
- **Environment variables**: Use for secrets and configuration
- **Pydantic Settings**: Centralized configuration management
- **Type safety**: All settings have proper type hints
- **Default values**: Sensible defaults for development
- **Validation**: Configuration validation on application startup

## Async Patterns
- **Parallel execution**: Use `asyncio.gather()` for concurrent operations
- **Context managers**: Proper resource management with async context managers
- **Error propagation**: Handle async exceptions properly
- **Coordination**: Message passing between agents for coordination