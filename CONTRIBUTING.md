# Contributing to GreenFlow AI 🌿

Thank you for your interest in contributing to GreenFlow AI! We welcome contributions of all kinds — bug fixes, new features, documentation improvements, and more.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

---

## 🤝 Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. Be kind, constructive, and professional in all interactions.

---

## 🚀 Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/your-username/greenflow-ai.git
   cd greenflow-ai
   ```
3. **Add upstream** remote:
   ```bash
   git remote add upstream https://github.com/original-owner/greenflow-ai.git
   ```

---

## 🛠 Development Setup

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# Install dependencies (including dev extras)
pip install -r requirements.txt
pip install pytest black isort flake8

# Copy environment config
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux

# Add your OPENAI_API_KEY to .env

# Start the development server
uvicorn greenflow.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🧑‍💻 How to Contribute

### Bug Fixes
1. Check if the bug is already reported in [Issues](../../issues)
2. If not, open a new issue describing the bug
3. Create a branch: `git checkout -b fix/your-bug-description`
4. Fix the bug and add tests
5. Submit a Pull Request

### New Features
1. Open an issue first to discuss the feature
2. Wait for maintainer feedback before coding
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Implement the feature with tests and documentation
5. Submit a Pull Request

### Documentation
1. Documentation lives in `/docs` and all `.md` files
2. Create a branch: `git checkout -b docs/your-improvement`
3. Make your changes and submit a Pull Request

---

## 🔃 Pull Request Process

1. **Sync** your fork with upstream before starting:
   ```bash
   git fetch upstream
   git merge upstream/main
   ```

2. **Work on a feature branch** — never commit directly to `main`

3. **Ensure all tests pass**:
   ```bash
   pytest tests/ -v
   ```

4. **Format your code**:
   ```bash
   black greenflow/
   isort greenflow/
   flake8 greenflow/
   ```

5. **Write a clear PR description** including:
   - What the change does
   - Why it's needed
   - Screenshots (for UI changes)
   - Related issues (use `Closes #123`)

6. **Request a review** from at least one maintainer

7. PRs are merged using **squash and merge**

---

## 📐 Coding Standards

| Tool | Usage |
|---|---|
| `black` | Code formatting (line length: 100) |
| `isort` | Import sorting |
| `flake8` | Linting |
| `mypy` | Optional type checking |

**Key principles:**
- Follow PEP 8 conventions
- Add type hints to all function signatures
- Write docstrings for all public functions and classes
- Keep functions small and focused (single responsibility)
- Prefer async functions for I/O-bound operations

**Example:**
```python
async def fetch_latest_record(db: AsyncSession) -> AnalyticsRecord | None:
    """
    Fetches the most recent analytics record from the database.

    Args:
        db: The async database session.

    Returns:
        The latest AnalyticsRecord, or None if no records exist.
    """
    result = await db.execute(
        select(AnalyticsRecord).order_by(AnalyticsRecord.timestamp.desc()).limit(1)
    )
    return result.scalar_one_or_none()
```

---

## 📝 Commit Message Guidelines

Use **Conventional Commits** format:

```
type(scope): short description

[optional body]
[optional footer]
```

**Types:**
| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Code restructuring |
| `test` | Adding or updating tests |
| `chore` | Build process, dependencies |

**Examples:**
```bash
feat(api): add CO2 prediction endpoint
fix(sse): resolve reconnection loop on error
docs(readme): update quick start instructions
test(analytics): add unit tests for risk scoring
```

---

## 🐛 Reporting Bugs

Open an issue with the **Bug Report** template and include:

- **Environment**: OS, Python version, package versions
- **Steps to reproduce**: Exact commands and inputs
- **Expected behavior**: What should have happened
- **Actual behavior**: What actually happened
- **Logs**: Paste relevant error messages / stack traces
- **Screenshots**: If applicable

---

## 💡 Suggesting Features

Open an issue with the **Feature Request** template and include:

- **Problem statement**: What problem does this solve?
- **Proposed solution**: Your idea for solving it
- **Alternatives considered**: Other approaches you thought of
- **Additional context**: Mockups, references, related issues

---

## 🙏 Thank You!

Every contribution, no matter how small, makes GreenFlow AI better. We appreciate your time and effort! 🌍
