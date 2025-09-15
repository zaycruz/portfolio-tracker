# Portfolio Tracker

A terminal-based portfolio tracker for managing investments across:
- **Cryptocurrency** holdings (manual input with live prices)
- **Hard assets** like gold, silver, and other precious metals (manual input with spot prices)

## Features

- 🔥 Real-time portfolio overview with asset allocation
- 📊 Detailed breakdowns with P&L calculations
- 💰 Live price feeds for crypto and precious metals
- 📈 Terminal-based dashboard with rich formatting
- 💾 Local data storage (no cloud dependencies)

## Installation

### Option 1: Automatic Installation
```bash
./install.sh
```

### Option 2: Manual Installation
1. **Clone or download** the portfolio tracker files
2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   ```
3. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```
4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

**First, activate the virtual environment:**
```bash
source venv/bin/activate
```

1. **Configure your settings:**
   ```bash
   python portfolio_tracker.py config
   ```

2. **Add crypto holdings:**
   ```bash
   python portfolio_tracker.py crypto add
   ```

3. **Add hard assets:**
   ```bash
   python portfolio_tracker.py assets add
   ```

4. **View your portfolio:**
   ```bash
   python portfolio_tracker.py show
   ```

5. **(Optional) Connect Robinhood for equities:**
   ```bash
   # Install optional dependency for live equities
   pip install robin-stocks python-dotenv

   # Configure credentials locally (stored in ~/.portfolio-tracker/config.json)
   python portfolio_tracker.py config   # Choose "Robinhood connection"

   # View equities positions and equity total
   python portfolio_tracker.py equities show
   ```

## Available Commands

### Portfolio Overview
- `show` - Display portfolio summary with allocation breakdown

### Cryptocurrency Management
- `crypto add` - Add a cryptocurrency holding
- `crypto remove` - Remove a cryptocurrency holding
- `crypto update` - Update crypto prices

### Hard Assets Management
- `assets add` - Add hard assets (gold, silver, etc.)
- `assets remove` - Remove hard assets
- `assets update` - Update precious metals spot prices

### Utilities
- `update` - Update all asset prices
- `config` - Configure settings

### Equities (Robinhood)
- `equities show` - Display live stock positions and total equity from Robinhood

## Data Storage

Portfolio data is stored locally in `~/.portfolio-tracker/`:
- `portfolio.json` - Your holdings and positions
- `config.json` - Settings and preferences

## API Dependencies

- **CoinGecko API** - Free crypto price feeds
- **GoldAPI.io / metals-api** - Precious metals spot prices (optional)

Set an API key if you want automatic spot prices for metals:

```bash
# Preferred: environment variable
export METALS_API_KEY="<your_key>"

# Or add to local config
mkdir -p ~/.portfolio-tracker
printf '{\n  "api_keys": { "metals_api": "<your_key>" }\n}\n' > ~/.portfolio-tracker/config.json
```

If no key is configured, the CLI will prompt you to enter metal prices manually when needed.

### Robinhood credentials

You can provide Robinhood credentials via either local config or environment variables. The CLI mirrors local config values into environment variables for convenience.

- Local config path: `~/.portfolio-tracker/config.json`
  ```json
  {
    "robinhood": {
      "username": "<your_username>",
      "password": "<your_password>",
      "account_number": "<your_account_number>"
    }
  }
  ```

- Environment variables (auto-populated from config on startup):
  - `USERNAME`
  - `PASSWORD`
  - `ACCOUNT_NUMBER`

Use the config wizard to set these securely on your machine:
```bash
pt config   # pick "Robinhood connection"
```

## Important Notes

🔒 **Security**: All data stored locally.

💡 **Tips**: 
- Run `update` command regularly to refresh prices
- Use detailed view for comprehensive P&L analysis
- Set up cost basis for accurate performance tracking

## Troubleshooting

**Missing dependencies**: Install with `pip install click rich requests`

**Price feed failures**: Most commands have fallback values and will continue to work.

**Robinhood not installed**: Install optional deps with `pip install robin-stocks python-dotenv`.

**Missing Robinhood credentials**: Run `pt config` and complete the Robinhood section, or set `USERNAME`, `PASSWORD`, and `ACCOUNT_NUMBER` env vars. The CLI mirrors config values to env on launch.

## Example Usage

```bash
# Install CLI (editable for development)
pip install -e .

# Or install the entry points with the helper
./install_cli.sh

# Initial setup
pt config                      # or: portfolio-tracker config

# Add investments
pt crypto add                  # or: portfolio-tracker crypto add
pt assets add

# Monitor portfolio
pt show
pt update                      # Refresh all prices

# Python entry is still supported
python3 portfolio_tracker.py show
```

Enjoy tracking your diversified portfolio! 🚀

## CI

A minimal GitHub Actions workflow validates packaging and CLI help on pushes and PRs. Networked tests are intentionally not run by default to avoid flakiness.

## Contributing

See `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` for guidelines.
