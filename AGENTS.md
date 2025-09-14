# Repository Guidelines

## Project Structure & Module Organization
- Root CLI: `portfolio_tracker.py` (Click-based commands, Rich output).
- Packaging: `setup.py` with console scripts `portfolio-tracker` and `pt`.
- Tests: `test_prices.py`, `test_interactive.py` (run as scripts).
- Config/data (user-local): `~/.portfolio-tracker/` → `portfolio.json`, `config.json`.
- Support files: `requirements.txt`, `install.sh`, `install_cli.sh`, `data_schema.json`.

## Build, Test, and Development Commands
- Setup venv: `python3 -m venv venv && source venv/bin/activate`.
- Install deps: `pip install -r requirements.txt`.
- Install CLI (editable): `./install_cli.sh` or `pip install -e .`.
- Run CLI: `python portfolio_tracker.py show` or `pt show` / `portfolio-tracker show`.
- Tests (networked): `python test_prices.py` and `python test_interactive.py`.

## Coding Style & Naming Conventions
- Python ≥ 3.8, PEP 8, 4-space indentation.
- Names: modules/files `snake_case.py`; functions/vars `snake_case`; classes `CamelCase`.
- CLI commands: lower-case verbs and nouns (e.g., `assets update`).
- Prefer small, pure functions for price fetch, parsing, and IO boundaries; add docstrings.
- Type hints encouraged for new/edited functions.

## Testing Guidelines
- Keep tests in files named `test_*.py` at repo root (consistent with current layout).
- Tests may call external APIs; expect network variability and rate limits.
  - When adding unit tests, mock HTTP via `unittest.mock` to avoid flakiness.
- Aim for meaningful coverage on parsing, calculations, and CLI option wiring.
- Quick run examples:
  - `python test_prices.py`
  - `python test_interactive.py`

## Commit & Pull Request Guidelines
- Commits: concise, imperative subject; include scope when helpful.
  - Examples: `feat(cli): add assets update command`, `fix(prices): handle CoinGecko timeout`.
- PRs: clear description, what/why, test notes, and manual run steps.
  - Link issues; include screenshots/terminal output for CLI changes.
  - Keep diffs focused; avoid drive-by refactors.

## Refactoring with ast-grep
- Use `ast-grep` for structural changes to reduce slop from regex edits.
- Install: `brew install ast-grep/ast-grep/ast-grep` or `cargo install ast-grep`.
- Dry run first: `sg -p python -e 'get_crypto_price($A)' -r 'fetch_crypto_price($A)' -n`.
- Apply in-place: `sg -p python -e 'get_crypto_price($A)' -r 'fetch_crypto_price($A)' -U`.
- Enforce timeouts example: `sg -p python -e 'requests.get($URL)' -r 'requests.get($URL, timeout=10)' -U`.
- Keep scope tight (stage only intended files) and run tests after rewrites.

## Security & Configuration Tips
- Do not commit files from `~/.portfolio-tracker/` or real API keys.
- Prefer reading secrets from local config (`config.json`) or env vars.
- Networked price tests can fail offline; mark such tests or provide fallbacks/mocks.

## Architecture Overview
- Single-file CLI orchestrates subcommands (`crypto`, `assets`, `show`, `update`, `interactive`).
- External services: CoinGecko (crypto), GoldAPI (metals). Handle timeouts and empty data defensively.
