# AGENTS.md

A simple, explicit guide for coding agents working on this Python project.

## Setup commands
- Create venv: `python3.10 -m venv .venv && source .venv/bin/activate`
- Upgrade tooling: `python -m pip install -U pip`
- Install dev deps: `pip install -r requirements-dev.txt`  
  *(If missing, run: `pip install ruff black isort pytest pytest-cov` and pin later.)*

## Code style (must-follow)
- **Line length:** 88 characters (Black default).
- **Imports:** Sorted by **isort** with the **black** profile.
- **Docstrings:** **PEP 257** with **Google style** sections (`Args`, `Returns`, `Raises`, etc.)
- **Typing:** Use type hints on public APIs; prefer `from __future__ import annotations` (py310+).

## Unit testing 

Unit test coverage should always be above 95%. Run the following bash to ensure this is met.

```bash
pytest --cov=pcs_pushover
```

## Linting & formatting (enforced)
Run these locally **before committing**; the CI will block if they fail.

```bash
ruff check --fix .
black .
isort . --profile black --line-length 88
```
