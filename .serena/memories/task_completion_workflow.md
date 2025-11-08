# Task Completion Workflow

## When a Task is Completed

After implementing any code changes or completing development tasks, follow this workflow to ensure code quality and project standards:

### 1. Code Quality Checks (REQUIRED)
```bash
# Fix linting issues
uv run ruff check --fix

# Format code  
uv run black .

# Type checking
uv run mypy src/gaggle
```

### 2. Testing (CRITICAL)
```bash
# Run relevant tests first
uv run pytest -k "relevant_test_pattern"

# Run full test suite
uv run pytest

# Check coverage
uv run pytest --cov=src/gaggle --cov-report=term-missing
```

### 3. Validation Requirements
- **All tests must pass** - No failing tests allowed in main branch
- **80% minimum coverage** - Coverage requirement enforced by pytest
- **Zero linting errors** - Ruff must pass cleanly  
- **Type check passes** - mypy must pass without errors

### 4. Pre-commit Hooks
```bash
# Run pre-commit hooks manually
uv run pre-commit run --all-files
```

### 5. Documentation Updates
Update relevant documentation files when making significant changes:
- **ARCHITECTURE.md** - Update implementation status
- **ROADMAP.md** - Mark components as completed with metrics
- **README.md** - Update feature status and performance metrics
- **CLAUDE.md** - Update development notes and current status

### 6. Testing Verification Process
Before claiming code "works" or is "functional":

```bash
# Test imports first
uv run python -c "from module.path import ClassName; print('Import successful')"

# Test basic functionality
uv run python simple_test.py

# Test with real dependencies (when available)
export ANTHROPIC_API_KEY=your_key
export GITHUB_TOKEN=your_token
uv run python test_functionality.py

# Run comprehensive test suite
uv run pytest tests/ -v
```

### 7. Status Claims Guidelines
- ✅ **Say "Architecture Implemented"** when code structure is complete
- ✅ **Say "Proof of Concept Working"** when basic functionality is verified  
- ❌ **Never say "Production Ready"** without end-to-end testing with real services
- ❌ **Never say "Fully Functional"** without comprehensive testing

### 8. Current Production Readiness Requirements
- **100% test pass rate** - No failing tests allowed
- **80% minimum code coverage** - Comprehensive testing required
- **All core functionality tested** - No stub implementations
- **Real service integration tested** - With actual API credentials

### 9. Git Workflow
```bash
# Check status
git status

# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: implement feature X with comprehensive tests"

# Only push when all checks pass
git push
```

### 10. Common Issues to Check
- **Import errors** - Ensure all imports work correctly
- **Pydantic v1 deprecations** - Use v2 syntax (@field_validator, etc.)
- **Missing dependencies** - Check that all required packages are installed
- **Test configuration** - Ensure pytest finds and runs all tests
- **Environment variables** - Set up required environment variables for testing

### 11. Quality Gates Checklist
- [ ] Code passes ruff linting
- [ ] Code formatted with black
- [ ] Type checking passes with mypy
- [ ] All tests pass (100% pass rate)
- [ ] Coverage meets 80% minimum
- [ ] Pre-commit hooks pass
- [ ] Documentation updated if needed
- [ ] Real functionality tested (when applicable)
- [ ] No deprecation warnings for project code

## Continuous Quality
- **Run tests frequently** during development
- **Use test-driven development** for new features
- **Keep test coverage high** - aim for >80%
- **Address warnings promptly** - don't let technical debt accumulate
- **Validate with real services** when possible (with proper credentials)