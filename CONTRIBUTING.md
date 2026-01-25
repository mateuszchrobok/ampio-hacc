# Contributing to Ampio-HACC

Thank you for your interest in contributing to the Ampio Home Assistant Custom Component!

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager (recommended)
- Access to an Ampio Smart Home system for testing

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/mateuszchrobok/ampio-hacc.git
   cd ampio-hacc
   ```

2. Install dependencies:
   ```bash
   uv sync --all-extras
   ```

3. Install pre-commit hooks:
   ```bash
   uv run pre-commit install
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=custom_components/ampio --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_models.py -v
```

### Code Quality

```bash
# Run linting
ruff check custom_components/ampio tests/
ruff format --check custom_components/ampio tests/

# Run type checking
uv run mypy custom_components/ampio --ignore-missing-imports

# Auto-fix linting issues
ruff check --fix custom_components/ampio tests/
ruff format custom_components/ampio tests/
```

### Validation

```bash
# Run hassfest validation (same as CI)
docker run --rm -v $(pwd):/github/workspace homeassistant/amd64-builder:dev \
  /bin/bash -c "pip install hassfest && hassfest"
```

## Code Style Guidelines

### Python

- Follow PEP 8 style guide
- Use type hints for all function parameters and return types
- Maximum line length: 100 characters
- Use `ruff` for linting and formatting

### Constants

- Use named constants instead of magic numbers
- Place constants in `const.py`
- Use `Final` type annotation for constants

### Logging

- Use appropriate log levels:
  - `DEBUG`: State updates, routine operations
  - `INFO`: Discovery progress, connections
  - `WARNING`: Recoverable errors, parse failures
  - `ERROR`: Connection issues, unrecoverable errors

### Error Handling

- Always log exceptions with context
- Use specific exception types (not bare `except:`)
- Include `json.JSONDecodeError` when handling JSON parsing

## Adding Support for New Modules

1. **Identify module type code** from Ampio documentation
2. **Create module info class** in `models.py`:
   ```python
   class MYMODULEModuleInfo(AmpioModuleInfo):
       """MY-MODULE Ampio module information."""

       def update_configs(self) -> None:
           """Update module specific configuration."""
           super().update_configs()
           # Add entity configurations
   ```

3. **Register in CLASS_FACTORY** in `models.py`
4. **Add tests** in `tests/test_models.py`
5. **Update documentation** in `docs/MQTT_PROTOCOL.md`

## Pull Request Process

1. Create a feature branch from `update_hacs`:
   ```bash
   git checkout -b feature/my-feature update_hacs
   ```

2. Make your changes with clear, atomic commits

3. Ensure all tests pass and code quality checks succeed

4. Update documentation if needed:
   - `CHANGELOG.md` - Add entry under [Unreleased]
   - `docs/` - Update relevant documentation

5. Submit a pull request with:
   - Clear description of changes
   - Link to related issues
   - Test plan or verification steps

## Reporting Issues

When reporting issues, please include:

- Home Assistant version
- Ampio Server version
- Ampio module types involved
- Relevant log messages (with DEBUG level if possible)
- Steps to reproduce

## Questions?

- Open an issue for questions or discussions
- Check existing issues for similar questions
