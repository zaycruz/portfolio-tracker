# Contributing

Thanks for your interest in contributing to Portfolio Tracker!

## Development setup
- Create a virtualenv: `python3 -m venv venv && source venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Install CLI (editable): `pip install -e .` or `./install_cli.sh`

## Running locally
- CLI help: `python portfolio_tracker.py --help` or `pt --help`
- Show portfolio: `pt show`

## Tests
- Networked tests can be flaky. Run manually:
  - `python tests/test_prices.py`
  - `python tests/test_interactive.py`
- When adding unit tests, mock HTTP calls with `unittest.mock`.

## Code style
- Python 3.8+, PEP 8, 4-space indentation.
- Small, pure functions for price fetch, parsing, and IO boundaries.
- Add docstrings and type hints for new/edited functions.

## Pull requests
- Keep diffs focused; avoid drive-by refactors.
- Use clear, imperative commit messages: `feat(cli): add assets update`.
- Include manual run steps and screenshots/output for CLI changes.

