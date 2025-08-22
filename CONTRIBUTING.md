# Contributing to MITM Toolkit

Thank you for your interest in contributing to MITM Toolkit! We welcome contributions from the community.

## How to Contribute

### Reporting Issues

1. Check existing issues to avoid duplicates
2. Use the issue templates when available
3. Include clear reproduction steps
4. Provide system information (OS, Python version, etc.)

### Suggesting Features

1. Open a discussion in the Issues section
2. Describe the use case clearly
3. Explain how it benefits users
4. Consider implementation complexity

### Code Contributions

#### Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/mitm-toolkit.git
   cd mitm-toolkit
   ```

3. Install development dependencies:
   ```bash
   uv pip install -e ".[dev]"
   ```

4. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

#### Development Guidelines

##### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Keep functions focused and small
- Write self-documenting code

##### Testing

- Write tests for new features
- Ensure existing tests pass
- Run tests before submitting:
  ```bash
  pytest tests/
  ```

##### Code Quality

Run quality checks:
```bash
# Format code
black mitm_toolkit/

# Lint
ruff check mitm_toolkit/

# Type checking
mypy mitm_toolkit/
```

##### Documentation

- Update README for user-facing changes
- Add docstrings to new functions/classes
- Include examples where helpful

#### Submitting Changes

1. Commit with clear messages:
   ```bash
   git commit -m "feat: add GraphQL introspection support"
   ```

2. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

3. Open a Pull Request:
   - Describe what changes you made
   - Explain why the changes are needed
   - Reference any related issues

### Plugin Development

Creating plugins is a great way to contribute:

1. Follow the plugin template in the documentation
2. Test thoroughly with different traffic patterns
3. Document configuration options
4. Submit as a PR or separate repository

## Security Contributions

For security issues, please see [SECURITY.md](SECURITY.md).

**DO NOT** open public issues for security vulnerabilities.

## Development Setup

### Prerequisites

- Python 3.10+
- uv or pip
- Git

### Environment Setup

```bash
# Clone repository
git clone https://github.com/binbandit/mitm-toolkit.git
cd mitm-toolkit

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=mitm_toolkit

# Specific test file
pytest tests/test_analyzer.py
```

## Code Review Process

1. Automated checks must pass
2. At least one maintainer review required
3. Comments and suggestions addressed
4. Final approval before merge

## Types of Contributions

### Priority Areas

- Performance improvements
- Additional protocol support (gRPC, WebSocket improvements)
- Enhanced AI analysis capabilities
- Better mock generation templates
- Documentation and examples

### Good First Issues

Look for issues labeled `good first issue` for beginner-friendly contributions.

## Community

- Be respectful and inclusive
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md)
- Help others in discussions
- Share your use cases and feedback

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- Documentation credits where appropriate

## Questions?

Feel free to:
- Open a discussion issue
- Ask in pull request comments
- Reach out to maintainers

Thank you for helping make MITM Toolkit better!