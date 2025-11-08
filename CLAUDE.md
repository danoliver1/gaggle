# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gaggle is an AI-powered Agile development team that simulates complete Scrum workflows using multi-agent systems. It uses different Claude model tiers optimized for specific team roles to achieve parallelism and cost efficiency:

- **Coordination Layer** (Haiku): Product Owner, Scrum Master
- **Architecture Layer** (Opus): Tech Lead for design decisions and code review  
- **Implementation Layer** (Sonnet): Frontend, Backend, Fullstack Developers
- **QA Layer** (Sonnet): QA Engineer for testing

## Development Commands

This project uses **uv** as the package manager. Key commands:

```bash
# Environment setup
uv sync --dev                    # Install all dependencies including dev tools
uv sync                         # Install only production dependencies

# Development
uv run gaggle --help            # Run the CLI application
uv run python -m gaggle.main    # Alternative way to run main module

# Code quality
uv run ruff check               # Lint code
uv run ruff check --fix         # Auto-fix linting issues
uv run black .                  # Format code
uv run mypy src/gaggle          # Type checking

# Testing
uv run pytest                   # Run all tests
uv run pytest tests/unit/       # Run unit tests only
uv run pytest tests/integration/ # Run integration tests
uv run pytest -k "test_name"    # Run specific test
uv run pytest --cov=src/gaggle  # Run with coverage

# Pre-commit hooks
uv run pre-commit install       # Install git hooks
uv run pre-commit run --all-files # Run all hooks manually
```

## Architecture Overview

### Core Philosophy
- **Agile over Waterfall**: Real sprints with planning, standups, reviews, retrospectives
- **Parallelism First**: Multiple agents work simultaneously rather than sequentially
- **Token Efficient**: Strategic use of different model tiers and reusable component generation
- **Real Team Dynamics**: Simulates actual Scrum team interactions

### Project Structure (Planned)
```
src/gaggle/
├── core/           # Sprint orchestration, team management, backlog, metrics
├── agents/         # Agent implementations by layer (coordination/architecture/implementation/qa)
├── workflows/      # Sprint workflow implementations (planning/execution/review/retrospective)
├── integrations/   # External services (GitHub, Strands, LLM providers)
├── models/         # Pydantic data models for sprints, stories, tasks, team
├── tools/          # Agent tools for GitHub, code generation, testing, reviews
└── config/         # Settings management and model configurations
```

### Key Design Patterns
- **Agent-Oriented Architecture**: Autonomous agents with clear responsibilities and message passing
- **Domain-Driven Design**: Rich domain models with business logic encapsulation
- **Clean Architecture**: Framework-independent core with dependency inversion
- **Async-First**: Parallel execution using `asyncio.gather()` for maximum efficiency

## Sprint Workflow Implementation

The core workflow follows this pattern:

1. **Sprint Planning**: Product Owner creates stories → Tech Lead analyzes and breaks down → Tech Lead generates reusable components → Scrum Master creates sprint plan
2. **Sprint Execution**: Daily standups → Parallel task execution by multiple developers → Tech Lead reviews code → Developers fix issues → QA tests in parallel
3. **Sprint Review & Retrospective**: Product Owner reviews work → Scrum Master facilitates retrospective

### Critical Implementation Details
- Tech Lead (Opus) generates reusable utilities **once per sprint** to save tokens during execution
- Multiple Sonnet developers work simultaneously rather than sequentially
- All agents use specialized tools matched to their responsibilities
- Cost optimization through strategic model assignment by role complexity

## GitHub Integration Strategy

Gaggle integrates deeply with GitHub for real development workflows:

- **Issues**: Structured templates for bugs, features, sprint stories, technical debt
- **Pull Requests**: Agents create and manage PRs with comprehensive templates
- **Projects**: Sprint boards and product backlog management
- **Actions**: Automated CI/CD and sprint execution workflows

## Key Dependencies

- **strands-agents**: Multi-agent orchestration framework
- **anthropic**: Claude API client for LLM interactions  
- **pygithub/githubkit**: GitHub API integration
- **pydantic**: Data validation and settings management
- **typer/rich**: CLI framework and terminal output
- **asyncio-throttle**: Rate limiting for parallel operations

## Important Files

- `example.py`: Reference implementation showing the multi-agent architecture (DO NOT MODIFY)
- `ARCHITECTURE.md`: Comprehensive production architecture documentation with implementation status
- `ROADMAP.md`: Research-driven implementation plan with Phase 1-2 completed, Phase 3 in progress
- `RESEARCH.md`: Research foundation and performance metrics (36% improvement from parallelization)
- `README.md`: Project overview and philosophy with current achievements

## Development Notes

- The project has **Phase 1 (Structured Communication) and Phase 2 (Hierarchical Memory) implemented and tested**
- **Phase 3 (Advanced Coordination Features)** is the next implementation target - see `ROADMAP.md` for details
- Token efficiency is critical - always consider model tier assignments and reusable component strategies
- Parallel execution is a core design principle - use async patterns throughout
- All agents should have clear separation of concerns and specialized tool sets
- Follow the Agile ceremony structure when implementing sprint workflows
- **Reference `ARCHITECTURE.md`** for detailed implementation status and file locations
- **Follow `ROADMAP.md`** for the research-driven implementation plan and success metrics

## Testing and Verification Requirements

**CRITICAL:** All code must be tested before claiming it works. Follow this verification process:

### Verification Steps for New Code

1. **Test Imports First**
   ```bash
   uv run python -c "from module.path import ClassName; print('Import successful')"
   ```

2. **Test Basic Functionality**
   ```bash
   uv run python simple_test.py  # Run basic functionality tests
   ```

3. **Test With Real Dependencies** (when available)
   ```bash
   # Set up real credentials
   export ANTHROPIC_API_KEY=your_key
   export GITHUB_TOKEN=your_token
   uv run python test_functionality.py
   ```

4. **Run Full Test Suite**
   ```bash
   uv run pytest tests/ -v
   ```

### Never Claim "Fully Functional" Without Testing

- ✅ **Say "Architecture Implemented"** when code structure is complete
- ✅ **Say "Proof of Concept Working"** when basic functionality is verified  
- ❌ **Never say "Production Ready"** without end-to-end testing with real services
- ❌ **Never say "Fully Functional"** without comprehensive testing

### Current Status Guidelines

- **Phase 1 (Structured Communication):** ✅ Fully implemented and tested (Message schemas, Agent state machines, Communication bus)
- **Phase 2 (Hierarchical Memory):** ✅ Fully implemented and tested (Multi-level memory, Context retrieval, Prompt caching)
- **Core Models:** ✅ Verified working (Sprint, UserStory, Task)
- **Agent Framework:** ✅ Basic creation and imports working
- **LLM Integration:** 🚧 Requires real credentials for testing
- **GitHub Integration:** 🚧 Requires real API tokens for testing  
- **End-to-End Workflows:** ❌ Not tested with real services

## Documentation Maintenance Requirements

**CRITICAL:** All documentation files must be kept up-to-date with implementation progress:

### Documentation Update Responsibilities

When making code changes, **always update these files accordingly**:

1. **ARCHITECTURE.md** - Update implementation status sections when features are completed
2. **ROADMAP.md** - Mark phases and components as completed with measured achievements  
3. **README.md** - Update feature status and performance metrics as they're achieved
4. **CLAUDE.md** - Update current status guidelines and development notes

### Documentation Update Triggers

Update documentation when:
- ✅ **New features implemented** - Update all four files with status changes
- ✅ **Tests pass** - Mark features as "tested and working" 
- ✅ **Performance metrics achieved** - Update with measured improvements
- ✅ **Architecture changes** - Document new patterns and structures
- ✅ **Research insights applied** - Update with evidence-based improvements

### Documentation Quality Standards

- **Specific over Generic**: Use exact percentages, file paths, and achievement metrics
- **Evidence-Based Claims**: Only claim "working" or "production-ready" with test evidence
- **Research Integration**: Reference specific research insights and measured outcomes
- **Status Accuracy**: Clearly distinguish between "implemented", "tested", and "production-ready"