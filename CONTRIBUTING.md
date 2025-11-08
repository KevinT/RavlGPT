# Contributing to RAVL

Thank you for your interest in contributing to RAVL! We welcome contributions from the community and appreciate your help in making this framework better.

## 📜 License

RAVL is licensed under the [Mozilla Public License 2.0 (MPL-2.0)](LICENSE). By contributing to this project, you agree that your contributions will be licensed under the same license.

### What This Means

- ✅ You can use RAVL for free (commercial or non-commercial)
- ✅ You can modify and distribute RAVL
- ✅ If you modify RAVL source files, you must share those modifications under MPL 2.0
- ✅ You can build proprietary extensions in separate files
- ✅ All contributions require attribution (copyright notices must be maintained)

## 🤝 How to Contribute

### 1. Types of Contributions Welcome

We welcome many types of contributions:

- 🐛 **Bug fixes** - Fix issues in the framework
- ✨ **New features** - Add capabilities to the RAVL framework
- 📚 **Documentation** - Improve guides, examples, and API docs
- 🧪 **Tests** - Add or improve test coverage
- 🎨 **Examples** - Create new loop examples and templates
- 🔌 **Integrations** - Add new mixins for third-party services
- 💬 **Issue reports** - Report bugs or request features

### 2. Before You Start

**For Bug Fixes:**
- Check if an issue already exists
- If not, create an issue describing the bug

**For New Features:**
- Open an issue to discuss the feature first
- Get feedback from maintainers before implementing
- Ensure it aligns with RAVL's design principles

**For Large Changes:**
- Discuss with maintainers in an issue first
- Break work into smaller, reviewable PRs when possible

### 3. Development Process

#### Setting Up Your Environment

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR-USERNAME/RavlGPT.git
cd RavlGPT

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Run tests to ensure everything works
pytest tests/ -v
```

#### Making Changes

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes
# - Follow existing code style
# - Add tests for new functionality
# - Update documentation as needed

# Run tests
pytest tests/ -v

# Run health checks (if applicable)
./bin/ravl-health health_check_ravl

# Commit your changes
git add .
git commit -m "Brief description of your changes"
```

#### Submitting a Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Open a Pull Request on GitHub
# - Provide a clear description of changes
# - Reference any related issues
# - Explain why the change is needed
```

### 4. Code Guidelines

#### Python Style

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to public functions and classes
- Keep functions focused and single-purpose

**Example:**

```python
def reflect(self) -> Dict[str, Any]:
    """
    Gather observations about current state.

    Returns:
        Dictionary containing:
        - state_hash: SHA256 hash of current state
        - items_found: Number of items discovered
        - last_modified: Timestamp of most recent change
    """
    # Implementation...
```

#### File Organization

- **Framework code** goes in `common/`
- **Project-specific loops** go in `ravl_loops/`
- **Templates** go in `templates/`
- **Documentation** goes in `docs/`
- **Tests** go in `tests/`

#### Testing Requirements

- Add unit tests for new functions (`tests/`)
- Add health checks for new loop patterns (`ravl_loops/health_checks/`)
- Ensure all tests pass before submitting PR
- Aim for >80% code coverage on new code

```bash
# Run tests with coverage
pytest tests/ --cov=common --cov-report=term-missing
```

### 5. Documentation

When adding features, please update:

- **README.md** - If it affects getting started or core features
- **docs/** - Add detailed guides for complex features
- **Docstrings** - Document all public APIs
- **Examples** - Provide working examples when appropriate
- **CHANGELOG.md** - Add entry under "Unreleased" section

### 6. Commit Message Guidelines

Write clear, concise commit messages:

```
Add support for Redis-backed model persistence

- Implement RedisModelStore class
- Add configuration options for Redis connection
- Include tests for Redis persistence
- Update documentation with Redis setup guide

Fixes #123
```

**Format:**
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed description with bullet points
- Reference issues/PRs at the end

### 7. Pull Request Review Process

1. **Automated Checks**: Tests must pass
2. **Code Review**: Maintainer will review your code
3. **Feedback**: Address any requested changes
4. **Approval**: Once approved, maintainer will merge
5. **Release**: Changes included in next release

**Review Timeline:**
- We aim to provide initial feedback within 3-5 business days
- Simple fixes may be merged faster
- Complex features may require more discussion

## 🎯 Contribution Ideas

Not sure where to start? Here are some ideas:

### Good First Issues
- Fix typos in documentation
- Add examples for common use cases
- Improve error messages
- Add more unit tests

### Medium Complexity
- Add new mixins for popular APIs
- Improve LLM provider integrations
- Create new loop templates
- Enhance CLI tooling

### Advanced
- Optimize performance of core execution engine
- Add new learning algorithms
- Improve failure recovery mechanisms
- Build visualization tools for loop diagnostics

## 📞 Getting Help

- **Questions?** Open a GitHub issue with the "question" label
- **Discussion?** Use GitHub Discussions
- **Security issues?** Email [maintainer email] privately

## 🙏 Attribution

When contributing:
- Keep existing copyright notices intact
- Add your copyright notice if you make substantial contributions
- Follow MPL 2.0 requirements for attribution

**Example header for substantial new files:**

```python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey
# Copyright (c) 2025 Your Name <your.email@example.com>
```

## 📋 Code of Conduct

We are committed to providing a welcoming and inclusive environment:

- ✅ Be respectful and considerate
- ✅ Welcome newcomers and help them learn
- ✅ Focus on what's best for the community
- ✅ Show empathy towards others
- ❌ No harassment or discriminatory behavior
- ❌ No trolling or insulting comments

## 📄 License Agreement

By submitting a contribution to this project, you:

1. Certify that you have the right to submit the contribution
2. Agree to license your contribution under MPL 2.0
3. Represent that your contribution is your original work
4. Understand that your contribution will be publicly available

This is the same agreement as the [Developer Certificate of Origin (DCO)](https://developercertificate.org/).

---

Thank you for contributing to RAVL! 🚀

**Questions?** Open an issue or reach out to the maintainers.
