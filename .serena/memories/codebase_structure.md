# Gaggle Codebase Structure

## Root Directory Layout
```
gaggle/
├── src/gaggle/              # Main source code
├── tests/                   # Test suite
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── research/                # Research documents and analysis
├── docker/                  # Docker configuration
├── .github/                 # GitHub workflows and templates
├── pyproject.toml           # Project configuration
├── pytest.ini              # Test configuration
├── README.md                # Project overview
├── ROADMAP.md               # Implementation roadmap
├── ARCHITECTURE.md          # Technical architecture
├── RESEARCH.md              # Research foundation
└── CLAUDE.md                # Claude Code integration guide
```

## Source Code Organization (`src/gaggle/`)
```
src/gaggle/
├── __init__.py              # Package initialization
├── main.py                  # CLI application entry point
│
├── agents/                  # Agent implementations
│   ├── base.py             # Base agent class
│   ├── coordination/       # Product Owner, Scrum Master
│   ├── architecture/       # Tech Lead
│   ├── implementation/     # Frontend, Backend, Fullstack developers
│   └── qa/                 # QA Engineer
│
├── core/                   # Core business logic
│   ├── sprint.py           # Sprint orchestration
│   ├── team.py             # Team management
│   ├── backlog.py          # Backlog management
│   ├── communication/      # Message bus and protocols
│   ├── memory/             # Hierarchical memory system
│   ├── coordination/       # Advanced coordination features
│   ├── state/              # State machines and context
│   └── production/         # Production infrastructure
│
├── models/                 # Pydantic data models
│   ├── __init__.py
│   ├── sprint.py           # Sprint domain model
│   ├── story.py            # User story model
│   ├── task.py             # Task model
│   ├── team.py             # Team configuration model
│   └── github.py           # GitHub integration models
│
├── workflows/              # Sprint workflow implementations
│   ├── __init__.py
│   ├── sprint_execution.py # Sprint execution workflow
│   └── daily_standup.py    # Daily standup workflow
│
├── tools/                  # Agent tools
│   ├── __init__.py
│   ├── project_tools.py    # Project management tools
│   ├── github_tools.py     # GitHub integration tools
│   ├── code_tools.py       # Code generation tools
│   ├── testing_tools.py    # Testing and QA tools
│   ├── review_tools.py     # Code review tools
│   └── integration_tools.py # Integration tools
│
├── integrations/           # External service integrations
│   ├── __init__.py
│   ├── llm_providers.py    # LLM provider integrations
│   ├── github_api.py       # GitHub API client
│   ├── strands_adapter.py  # Strands framework adapter
│   ├── cicd_pipelines.py   # CI/CD integration
│   └── github/             # Detailed GitHub integration
│       ├── client.py
│       ├── issues.py
│       ├── pull_requests.py
│       └── projects.py
│
├── config/                 # Configuration management
│   ├── __init__.py
│   ├── settings.py         # Application settings
│   └── models.py           # Configuration models
│
├── utils/                  # Shared utilities
│   ├── __init__.py
│   ├── logging.py          # Logging configuration
│   ├── token_counter.py    # Token usage tracking
│   ├── cost_calculator.py  # Cost calculation
│   └── async_utils.py      # Async utilities
│
├── optimization/           # Cost and performance optimization
│   └── cost_optimizer.py   # Cost optimization algorithms
│
├── learning/               # Multi-sprint learning
│   └── multi_sprint_optimizer.py # Learning algorithms
│
├── dashboards/             # Metrics and monitoring
│   └── sprint_metrics.py   # Sprint metrics dashboard
│
├── teams/                  # Team composition
│   └── custom_compositions.py # Custom team configurations
│
└── api/                    # Optional API framework
    ├── routes/             # API route definitions
    └── middleware/         # API middleware
```

## Test Structure (`tests/`)
```
tests/
├── __init__.py
├── conftest.py             # Pytest configuration and fixtures
├── unit/                   # Unit tests
├── integration/            # Integration tests
├── end_to_end/            # End-to-end tests
└── fixtures/              # Test data and fixtures
```

## Key Files and Their Purposes

### Configuration Files
- **`pyproject.toml`**: Project metadata, dependencies, tool configurations
- **`pytest.ini`**: Test configuration with comprehensive markers
- **`.pre-commit-config.yaml`**: Pre-commit hooks configuration

### Documentation Files
- **`README.md`**: Project overview and quick start guide
- **`ROADMAP.md`**: Research-driven implementation plan (all phases complete)
- **`ARCHITECTURE.md`**: Comprehensive production architecture documentation
- **`RESEARCH.md`**: Research foundation and performance metrics
- **`CLAUDE.md`**: Claude Code integration guidelines

### Entry Points
- **`src/gaggle/main.py`**: CLI application with typer framework
- **`demo.py`**: Demonstration script showing sprint planning
- **`example.py`**: Reference implementation (DO NOT MODIFY)

### Core Models
- **`models/sprint.py`**: Complete sprint lifecycle with metrics and validation
- **`models/story.py`**: User stories with acceptance criteria and business logic
- **`models/task.py`**: Detailed tasks with dependencies and tracking
- **`models/team.py`**: Team configuration and performance tracking

### Agent Implementations
- **`agents/coordination/product_owner.py`**: Requirements analysis and backlog management
- **`agents/coordination/scrum_master.py`**: Sprint facilitation and metrics
- **`agents/architecture/tech_lead.py`**: Technical analysis and code review
- **`agents/implementation/`**: Developer agents (frontend, backend, fullstack)
- **`agents/qa/qa_engineer.py`**: Quality assurance and testing

### Advanced Features
- **`core/communication/`**: Structured message bus and protocols
- **`core/memory/`**: Hierarchical memory with intelligent retrieval
- **`core/coordination/`**: Advanced sprint coordination features
- **`optimization/`**: Cost optimization and token efficiency
- **`learning/`**: Multi-sprint learning and pattern recognition

## Import Patterns
- **Absolute imports**: Always use absolute imports from `gaggle` package
- **Module organization**: Group related functionality in packages
- **Clear dependencies**: Dependencies flow from outer layers to core domain
- **Type safety**: Comprehensive type hints throughout codebase