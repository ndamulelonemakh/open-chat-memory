# Contributing to Open Chat Memory

Thank you for your interest in contributing to Open Chat Memory! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/open-chat-memory.git
   cd open-chat-memory
   ```
3. **Add the upstream repository**:
   ```bash
   git remote add upstream https://github.com/ndamulelonemakh/open-chat-memory.git
   ```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- PostgreSQL (for database testing)
- Git

### Setting Up Your Environment

1. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install the package in development mode**:
   ```bash
   pip install -e ".[db,mem0]"
   ```

3. **Install development dependencies**:
   ```bash
   pip install pytest pytest-cov ruff mypy
   ```

4. **Run tests to verify setup**:
   ```bash
   pytest -q
   ```

## How to Contribute

### Types of Contributions

We welcome many types of contributions:

- **Bug fixes**: Fix issues reported in the issue tracker
- **New features**: Add support for new chat providers, databases, or memory stores
- **Documentation**: Improve README, docstrings, or add examples
- **Tests**: Increase test coverage
- **Performance improvements**: Optimize parsing or loading operations

### Before You Start

1. **Check existing issues** to see if someone is already working on it
2. **Open an issue** to discuss major changes before implementing them
3. **Keep changes focused**: One feature or fix per pull request

## Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [ruff](https://docs.astral.sh/ruff/) for linting and formatting
- Use type hints for all function signatures
- Maximum line length: 100 characters

### Code Formatting

Run ruff before committing:

```bash
# Check formatting
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

### Type Checking

Run mypy for type checking:

```bash
mypy openchatmemory
```

### Documentation

- Add docstrings to all public modules, classes, and functions
- Use Google-style docstrings
- Include usage examples in docstrings where appropriate

Example:

```python
def parse_messages(file_path: Path) -> List[MessageModel]:
    """Parse chat messages from an export file.
    
    Args:
        file_path: Path to the chat export file
        
    Returns:
        List of normalized message models
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is invalid
        
    Example:
        >>> parser = ChatGPTParser()
        >>> messages = parser.parse(Path("conversations.json"))
        >>> len(messages)
        150
    """
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=openchatmemory --cov-report=html

# Run specific test file
pytest tests/test_parsers.py

# Run with verbose output
pytest -v
```

### Writing Tests

- Write tests for all new features
- Maintain or improve code coverage (target: 80%+)
- Use descriptive test names: `test_parser_handles_empty_conversation`
- Use fixtures for common test data
- Test both success and failure cases

Example test structure:

```python
def test_chatgpt_parser_basic_conversation():
    """Test ChatGPT parser with a basic conversation."""
    parser = ChatGPTParser()
    messages = parser.parse(Path("tests/fixtures/chatgpt_basic.json"))
    
    assert len(messages) == 3
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
```

## Submitting Changes

### Commit Messages

Write clear, descriptive commit messages:

- Use present tense: "Add feature" not "Added feature"
- Use imperative mood: "Move file to" not "Moves file to"
- First line should be 50 characters or less
- Provide detailed description in the commit body if needed

Good commit message examples:

```
Add support for Grok chat exports

- Implement GrokParser class
- Add tests for Grok parser
- Update README with Grok usage examples
```

```
Fix memory leak in postgres loader

The batch insert was not clearing the list after commit,
causing memory to grow linearly with dataset size.
```

### Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/add-grok-support
   ```

2. **Make your changes** and commit them

3. **Keep your branch up to date**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

4. **Push to your fork**:
   ```bash
   git push origin feature/add-grok-support
   ```

5. **Open a Pull Request** on GitHub

6. **Describe your changes** in the PR description:
   - What problem does it solve?
   - How does it solve it?
   - Are there any breaking changes?
   - Related issues (use "Fixes #123" or "Closes #123")

7. **Respond to review feedback** promptly

8. **Ensure CI passes** before requesting review

### PR Checklist

Before submitting your PR, ensure:

- [ ] Code follows the project's style guidelines
- [ ] Tests pass locally (`pytest`)
- [ ] New code has tests
- [ ] Documentation is updated (README, docstrings)
- [ ] Commit messages are clear and descriptive
- [ ] CHANGELOG.md is updated (for notable changes)
- [ ] No merge conflicts with main branch

## Reporting Bugs

### Before Submitting a Bug Report

- Check the [existing issues](https://github.com/ndamulelonemakh/open-chat-memory/issues)
- Try the latest version from the main branch
- Collect relevant information about your environment

### Bug Report Template

When filing a bug, include:

1. **Description**: Clear description of the bug
2. **Steps to Reproduce**: Minimal steps to reproduce the issue
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**:
   - OS and version
   - Python version
   - Package version
   - Relevant dependencies
6. **Additional Context**: Logs, screenshots, or sample data

## Suggesting Enhancements

We welcome feature suggestions! When suggesting an enhancement:

1. **Check existing issues** to avoid duplicates
2. **Provide a clear use case**: Why is this feature needed?
3. **Describe the solution**: How should it work?
4. **Consider alternatives**: Are there other ways to solve the problem?
5. **Be open to feedback**: The maintainers may suggest modifications

## Questions?

If you have questions about contributing:

- Open a [GitHub Discussion](https://github.com/ndamulelonemakh/open-chat-memory/discussions)
- Check existing documentation and issues
- Reach out to maintainers via email

## Recognition

Contributors will be recognized in:

- The project's README
- Release notes for significant contributions
- GitHub's contributor graph

Thank you for helping make Open Chat Memory better! 🎉
