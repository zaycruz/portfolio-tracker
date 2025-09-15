#!/usr/bin/env python3
"""
Portfolio Tracker CLI - Track Crypto and Hard Assets
"""

import click
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
import requests
from services import robinhood_port


console = Console()

# Data file paths
DATA_DIR = Path.home() / '.portfolio-tracker'
PORTFOLIO_FILE = DATA_DIR / 'portfolio.json'
CONFIG_FILE = DATA_DIR / 'config.json'

def ensure_data_dir():
    """Ensure data directory exists"""
    DATA_DIR.mkdir(exist_ok=True)

def load_portfolio():
    """Load portfolio data"""
    if not PORTFOLIO_FILE.exists():
        return {
            "crypto": {"holdings": []},
            "hard_assets": {"precious_metals": [], "other": []},
            "cash": {"balance": 0.0, "currency": "USD"},
            "summary": {"total_value": 0.0, "allocation": {}, "last_calculated": None}
        }
    
    with open(PORTFOLIO_FILE, 'r') as f:
        data = json.load(f)
        # Backfill missing sections for backward compatibility
        if 'cash' not in data:
            data['cash'] = {"balance": 0.0, "currency": "USD"}
        if 'crypto' not in data:
            data['crypto'] = {"holdings": []}
        if 'hard_assets' not in data:
            data['hard_assets'] = {"precious_metals": [], "other": []}
        return data

def save_portfolio(portfolio):
    """Save portfolio data"""
    ensure_data_dir()
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portfolio, f, indent=2)

def load_config():
    """Load configuration"""
    if not CONFIG_FILE.exists():
        return {
            "api_keys": {"coingecko": "", "metals_api": ""},
            "preferences": {"currency": "USD", "update_frequency": 300, "show_cost_basis": True}
        }
    
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    """Save configuration"""
    ensure_data_dir()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def sync_env_from_config(config: dict) -> None:
    """Populate standard env vars from local config if present.

    Mirrors config["robinhood"] values into environment variables commonly
    used by integrations so that downstream libraries can discover them.
    """
    try:
        rh = (config or {}).get("robinhood") or {}
        mapping = {
            "USERNAME": rh.get("username"),
            "PASSWORD": rh.get("password"),
            "ACCOUNT_NUMBER": rh.get("account_number"),
        }
        for key, val in mapping.items():
            if val:
                os.environ[key] = str(val)
    except Exception:
        # Never let env sync break the CLI
        pass


def _get_rh_config(config: dict) -> dict:
    """Return the nested Robinhood config dict (creating structure if missing)."""
    if not isinstance(config, dict):
        config = {}
    if not config.get("robinhood"):
        config["robinhood"] = {"username": "", "password": "", "account_number": ""}
    else:
        # Backfill any missing keys
        rh = config["robinhood"]
        rh.setdefault("username", "")
        rh.setdefault("password", "")
        rh.setdefault("account_number", "")
    return config


def _configure_robinhood_interactive(config: dict) -> dict:
    """Interactive prompts to capture Robinhood credentials and persist them.

    Prompts for username and account number, and optionally updates the
    password (input hidden). Returns the updated config dict.
    """
    config = _get_rh_config(config)
    rh_cfg = config["robinhood"]

    console.print(Panel.fit("🔐 Robinhood Connection", style="bold blue"))

    current_user = rh_cfg.get("username") or ""
    current_acct = rh_cfg.get("account_number") or ""

    # Username and account number (show current as default if present)
    username = Prompt.ask("Robinhood username", default=current_user) if current_user else Prompt.ask("Robinhood username")
    account_number = (
        Prompt.ask("Robinhood account number", default=current_acct)
        if current_acct else
        Prompt.ask("Robinhood account number")
    )

    # Password – ask whether to update to avoid forcing re-entry
    update_pwd = click.confirm("Update password now?", default=(not bool(rh_cfg.get("password"))))
    if update_pwd:
        # Use click.prompt to hide input and confirm
        password = click.prompt("Robinhood password", hide_input=True, confirmation_prompt=True)
        rh_cfg["password"] = password

    rh_cfg["username"] = username.strip()
    rh_cfg["account_number"] = account_number.strip()

    save_config(config)
    # Reflect into env for current process
    sync_env_from_config(config)

    # Try a light validation if the optional dependency is present
    result = robinhood_port.get_portfolio_data(config)
    err = result.get("error")
    if err == "missing_credentials":
        console.print("[red]Credentials incomplete. Please ensure username, password, and account number are set.[/red]")
    elif isinstance(err, str) and err.startswith("login_or_fetch_failed"):
        console.print(f"[red]Login failed: {err}[/red]")
    elif err == "robin-stocks not installed":
        console.print("[yellow]robin-stocks not installed. Install with: pip install robin-stocks[/yellow]")
    else:
        console.print("[green]✓ Robinhood configuration saved[/green]")

    return config


def convert_to_ounces(quantity, unit):
    """Convert a quantity to ounces from a given unit."""
    if unit.lower() in ['g', 'gram', 'grams']:
        return quantity / 31.1034768
    # Add other conversions here if needed
    return quantity

def get_robinhood_portfolio():
    """Get the Robinhood portfolio data using config/env if available"""
    cfg = load_config()
    sync_env_from_config(cfg)
    return robinhood_port.get_portfolio_data(cfg)

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """🔥 Portfolio Tracker - Track your investments across crypto and hard assets
    
    A comprehensive CLI tool to manage and monitor your investment portfolio including:
    • Cryptocurrency holdings with live prices
    • Hard assets (precious metals, collectibles)
    • Real-time portfolio valuation and allocation breakdown
    
    Quick Start:
        portfolio-tracker               # Enter interactive mode
        portfolio-tracker show          # View your portfolio
        portfolio-tracker config        # Configure your settings
        portfolio-tracker interactive   # Enter interactive mode explicitly
    
    For detailed help on any command, use: portfolio-tracker COMMAND --help
    """
    # Make sure env reflects local config early
    try:
        sync_env_from_config(load_config())
    except Exception:
        pass

    if ctx.invoked_subcommand is None:
        # No subcommand was provided, start interactive mode
        ctx.invoke(interactive)

def get_crypto_price(symbol):
    """Get current crypto price from CoinGecko"""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if symbol in data and 'usd' in data[symbol]:
            return data[symbol]['usd']
        else:
            console.print(f"[red]Error: No price data found for {symbol}[/red]")
            return None
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Network error fetching crypto price: {e}[/red]")
        return None
    except KeyError as e:
        console.print(f"[red]Price data format error for {symbol}: {e}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]Error fetching crypto price: {e}[/red]")
        return None

def search_crypto_id(search_term):
    """Search for crypto ID on CoinGecko using the proper search endpoint"""
    try:
        url = f"https://api.coingecko.com/api/v3/search?query={search_term}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('coins'):
            # The first result is usually the most relevant
            best_match = data['coins'][0]
            return best_match['id'], best_match['name']
        else:
            return None, None
            
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Network error during crypto search: {e}[/red]")
        return None, None
    except Exception as e:
        console.print(f"[red]An error occurred during crypto search: {e}[/red]")
        return None, None

@cli.group()
def crypto():
    """₿ Cryptocurrency management commands
    
    Track your cryptocurrency holdings with live price updates from CoinGecko.
    Supports thousands of cryptocurrencies with automatic price discovery.
    
    Commands:
        add       Add a new crypto holding to your portfolio  
        remove    Remove a crypto holding from your portfolio
        update    Update all crypto prices with latest market data
    
    Example Usage:
        portfolio-tracker crypto add       # Add Bitcoin, Ethereum, etc.
        portfolio-tracker crypto update    # Refresh all crypto prices
        portfolio-tracker crypto remove    # Remove a holding
    """
    pass

@crypto.command()
def add():
    """➕ Add a cryptocurrency holding to your portfolio
    
    Search and add any cryptocurrency by symbol (BTC, ETH) or name (Bitcoin, Ethereum).
    The system will automatically find the correct coin and fetch current market prices.
    
    You can optionally specify your average cost basis for P&L tracking.
    """
    portfolio = load_portfolio()
    
    # Get crypto symbol or name
    search_term = click.prompt("Enter cryptocurrency symbol or name (e.g., BTC, Bitcoin)")
    
    # Search for the crypto
    console.print(f"[yellow]Searching for {search_term}...[/yellow]")
    crypto_id, crypto_name = search_crypto_id(search_term)
    
    if not crypto_id:
        console.print(f"[red]Could not find cryptocurrency: {search_term}[/red]")
        return
    
    console.print(f"[green]Found: {crypto_name} ({crypto_id})[/green]")
    
    # Get quantity
    quantity = click.prompt("Enter quantity", type=float)
    
    # Get average cost (optional)
    avg_cost = click.prompt("Enter average cost per unit (USD)", type=float, default=0.0)
    
    # Get current price
    console.print("[yellow]Fetching current price...[/yellow]")
    current_price = get_crypto_price(crypto_id)
    
    if current_price is None:
        console.print("[yellow]Could not fetch current price, setting to 0[/yellow]")
        current_price = 0.0
    
    # Add to portfolio
    holding = {
        "symbol": crypto_id,
        "name": crypto_name,
        "quantity": quantity,
        "average_cost": avg_cost,
        "current_price": current_price,
        "last_updated": datetime.now().isoformat()
    }
    
    portfolio['crypto']['holdings'].append(holding)
    save_portfolio(portfolio)
    
    console.print(f"[green]✓ Added {quantity} {crypto_name} to portfolio[/green]")
    if current_price > 0:
        total_value = quantity * current_price
        console.print(f"Current value: ${total_value:,.2f}")

@crypto.command()
def remove():
    """➖ Remove a cryptocurrency holding from your portfolio
    
    Select from your current crypto holdings to remove from tracking.
    This will permanently delete the holding data from your portfolio.
    """
    portfolio = load_portfolio()
    
    if not portfolio['crypto']['holdings']:
        console.print("[yellow]No crypto holdings found[/yellow]")
        return
    
    # Show current holdings
    console.print("\nCurrent holdings:")
    for i, holding in enumerate(portfolio['crypto']['holdings']):
        console.print(f"{i+1}. {holding['name']} ({holding['quantity']} units)")
    
    # Get selection
    choice = click.prompt("Enter number to remove", type=int) - 1
    
    if 0 <= choice < len(portfolio['crypto']['holdings']):
        removed = portfolio['crypto']['holdings'].pop(choice)
        save_portfolio(portfolio)
        console.print(f"[green]✓ Removed {removed['name']} from portfolio[/green]")
    else:
        console.print("[red]Invalid selection[/red]")

@crypto.command(name="adjust")
@click.option('--symbol', '-s', type=str, default=None, help='CoinGecko id or name of the crypto to adjust (e.g., bitcoin)')
@click.option('--set', 'set_qty', type=float, default=None, help='Set quantity to an exact value')
@click.option('--add', 'add_qty', type=float, default=None, help='Amount to add to current quantity')
@click.option('--subtract', 'sub_qty', type=float, default=None, help='Amount to subtract from current quantity')
def crypto_adjust(symbol: str, set_qty: float, add_qty: float, sub_qty: float):
    """Adjust quantity of an existing crypto holding.
    Examples:
      pt crypto adjust --symbol bitcoin --add 0.0054
      pt crypto adjust --symbol bitcoin --subtract 0.01
      pt crypto adjust --symbol bitcoin --set 0.2154
    If no flags are provided, prompts to select holding and operation.
    """
    portfolio = load_portfolio()
    holdings = portfolio.get('crypto', {}).get('holdings', [])
    if not holdings:
        console.print("[yellow]No crypto holdings to adjust[/yellow]")
        return
    # Resolve holding
    idx = None
    if symbol:
        # Allow match on id or name (case-insensitive)
        s = symbol.strip().lower()
        for i, h in enumerate(holdings):
            if h.get('symbol', '').lower() == s or h.get('name', '').lower() == s:
                idx = i
                break
        if idx is None:
            console.print(f"[red]Holding not found for: {symbol}[/red]")
            return
    else:
        console.print("\nSelect holding to adjust:")
        for i, h in enumerate(holdings, 1):
            console.print(f"{i}. {h.get('name','?')} ({h.get('symbol','?')}): {h.get('quantity',0)}")
        choice = click.prompt("Enter number", type=int) - 1
        if 0 <= choice < len(holdings):
            idx = choice
        else:
            console.print("[red]Invalid selection[/red]")
            return
    holding = holdings[idx]
    current_qty = float(holding.get('quantity', 0.0))
    # Determine operation
    ops = [x is not None for x in (set_qty, add_qty, sub_qty)]
    if sum(ops) > 1:
        console.print("[red]Use only one of --set, --add, or --subtract[/red]")
        return
    if not any(ops):
        op = Prompt.ask("Operation", choices=["set", "add", "subtract"], default="add")
        amount = click.prompt("Amount", type=float)
        if op == 'set':
            new_qty = amount
        elif op == 'add':
            new_qty = current_qty + amount
        else:
            new_qty = current_qty - amount
    else:
        if set_qty is not None:
            new_qty = float(set_qty)
        elif add_qty is not None:
            new_qty = current_qty + float(add_qty)
        else:
            new_qty = current_qty - float(sub_qty)
    if new_qty < 0:
        console.print("[red]Quantity cannot be negative[/red]")
        return
    holding['quantity'] = new_qty
    holding['last_updated'] = datetime.now().isoformat()
    save_portfolio(portfolio)
    console.print(f"[green]✓ Updated {holding.get('name','')} quantity: {current_qty} → {new_qty}")


def get_metals_price(metal_type):
    """Get precious metals spot price.

    Attempts to fetch from GoldAPI.io if an API key is available via env vars
    (METALS_API_KEY, GOLDAPI_API_KEY, or GOLDAPI_KEY) or config.json
    (api_keys.metals_api). Returns None if no key is configured or on failure.
    """
    # Resolve API key from env or local config
    api_key = (
        os.getenv("METALS_API_KEY")
        or os.getenv("GOLDAPI_API_KEY")
        or os.getenv("GOLDAPI_KEY")
        or load_config().get("api_keys", {}).get("metals_api")
    ) or ""
    
    # Map metal types to API symbols
    symbol_map = {
        'gold': 'XAU',
        'silver': 'XAG', 
        'platinum': 'XPT',
        'palladium': 'XPD'
    }
    
    symbol = symbol_map.get(metal_type.lower())
    if not symbol:
        console.print(f"[red]Unsupported metal type: {metal_type}[/red]")
        return None
        
    try:
        if not api_key:
            console.print("[yellow]No metals API key configured. Set METALS_API_KEY or add to config.json.[/yellow]")
            return None

        url = f"https://www.goldapi.io/api/{symbol}/USD"
        headers = {
            "x-access-token": api_key,
            "Content-Type": "application/json",
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # GoldAPI returns price per troy ounce
        if 'price' in data:
            return float(data['price'])
        else:
            console.print(f"[red]No price data in response for {metal_type}[/red]")
            return None
            
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Network error fetching {metal_type} price: {e}[/red]")
        return None
    except (KeyError, ValueError) as e:
        console.print(f"[red]Price data format error for {metal_type}: {e}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]Error fetching {metal_type} price: {e}[/red]")
        return None

@cli.group()
def hard_assets():
    """🥇 Hard assets management commands
    
    Track physical assets including precious metals (gold, silver, platinum, palladium)
    and other collectibles or commodities. Includes live spot price updates.
    
    Commands:
        add       Add a hard asset to your portfolio
        remove    Remove a hard asset from your portfolio  
        update    Update spot prices for precious metals
    
    Example Usage:
        portfolio-tracker assets add       # Add gold coins, silver bars, etc.
        portfolio-tracker assets update    # Refresh metal spot prices
        portfolio-tracker assets remove    # Remove an asset
    """
    pass

@hard_assets.command()
def add():
    """➕ Add a hard asset to your portfolio
    
    Add physical assets including:
    • Precious metals (gold, silver, platinum, palladium) - with live spot pricing
    • Collectibles, commodities, and other physical investments
    
    Specify quantity, unit of measurement, and your average cost basis.
    """
    portfolio = load_portfolio()
    
    # Asset type selection
    asset_types = ['gold', 'silver', 'platinum', 'palladium', 'other']
    console.print("\nSelect asset type:")
    for i, asset_type in enumerate(asset_types, 1):
        console.print(f"{i}. {asset_type.title()}")
    
    choice = click.prompt("Enter choice", type=int) - 1
    if choice < 0 or choice >= len(asset_types):
        console.print("[red]Invalid choice[/red]")
        return
    
    asset_type = asset_types[choice]
    
    # Get asset details
    if asset_type == 'other':
        asset_name = click.prompt("Enter asset name")
        asset_type = click.prompt("Enter asset type (e.g., copper, collectible)")
    else:
        asset_name = f"{asset_type.title()}"
    
    quantity = click.prompt("Enter quantity", type=float)
    unit = click.prompt("Enter unit (e.g., oz, g, lbs)", default="oz")
    avg_cost = click.prompt("Enter average cost per unit (USD)", type=float, default=0.0)
    
    # Get current spot price for precious metals
    current_price = 0.0
    if asset_type in ['gold', 'silver', 'platinum', 'palladium']:
        console.print("[yellow]Fetching current spot price...[/yellow]")
        current_price = get_metals_price(asset_type)
        if current_price:
            console.print(f"Current {asset_type} spot price: ${current_price:.2f}/oz")
        else:
            console.print("[yellow]Could not fetch spot price[/yellow]")
            current_price = click.prompt("Enter current price manually", type=float, default=0.0)
    else:
        current_price = click.prompt("Enter current market value per unit", type=float, default=0.0)
    
    # Create asset entry
    asset_data = {
        "name": asset_name,
        "type": asset_type,
        "unit": unit,
        "quantity": quantity,
        "average_cost": avg_cost,
        "current_spot_price": current_price,
        "last_updated": datetime.now().isoformat()
    }
    
    # Add to appropriate category
    if asset_type in ['gold', 'silver', 'platinum', 'palladium']:
        portfolio['hard_assets']['precious_metals'].append(asset_data)
    else:
        portfolio['hard_assets']['other'].append(asset_data)
    
    save_portfolio(portfolio)
    
    console.print(f"[green]✓ Added {quantity} {unit} of {asset_name} to portfolio[/green]")
    if current_price > 0:
        quantity_in_ounces = convert_to_ounces(quantity, unit)
        total_value = quantity_in_ounces * current_price
        console.print(f"Current value: ${total_value:,.2f}")


@hard_assets.command()
def remove():
    """➖ Remove a hard asset from your portfolio
    
    Select from your current hard assets to remove from tracking.
    This will permanently delete the asset data from your portfolio.
    """
    portfolio = load_portfolio()
    
    all_assets = []
    all_assets.extend(portfolio['hard_assets']['precious_metals'])
    all_assets.extend(portfolio['hard_assets']['other'])
    
    if not all_assets:
        console.print("[yellow]No hard assets found[/yellow]")
        return
    
    # Show current assets
    console.print("\nCurrent assets:")
    for i, asset in enumerate(all_assets):
        console.print(f"{i+1}. {asset['name']} ({asset['quantity']} {asset['unit']})")
    
    choice = click.prompt("Enter number to remove", type=int) - 1
    
    if 0 <= choice < len(all_assets):
        asset_to_remove = all_assets[choice]
        
        # Remove from the correct category
        if asset_to_remove in portfolio['hard_assets']['precious_metals']:
            portfolio['hard_assets']['precious_metals'].remove(asset_to_remove)
        else:
            portfolio['hard_assets']['other'].remove(asset_to_remove)
        
        save_portfolio(portfolio)
        console.print(f"[green]✓ Removed {asset_to_remove['name']} from portfolio[/green]")
    else:
        console.print("[red]Invalid selection[/red]")

@hard_assets.command()
def update():
    """🔄 Update hard asset prices with latest spot prices
    
    Fetch current spot prices for precious metals (gold, silver, platinum, palladium).
    This updates your portfolio with real-time market pricing for accurate valuation.
    """
    portfolio = load_portfolio()
    
    all_assets = []
    all_assets.extend(portfolio['hard_assets']['precious_metals'])
    all_assets.extend(portfolio['hard_assets']['other'])
    
    if not all_assets:
        console.print("[yellow]No hard assets to update[/yellow]")
        return
    
    console.print("[yellow]Updating asset prices...[/yellow]")
    updated_count = 0
    
    for asset in portfolio['hard_assets']['precious_metals']:
        if asset['type'] in ['gold', 'silver', 'platinum', 'palladium']:
            new_price = get_metals_price(asset['type'])
            if new_price:
                asset['current_spot_price'] = new_price
                asset['last_updated'] = datetime.now().isoformat()
                updated_count += 1
                console.print(f"Updated {asset['name']}: ${new_price:.2f}/{asset['unit']}")
    
    save_portfolio(portfolio)
    console.print(f"[green]✓ Updated {updated_count} asset prices[/green]")


@cli.group()
def assets():
    """🥇 Hard assets management commands"""
    

@cli.group()
def equities():
    """📈 Equities (brokerage) management commands"""
    pass

@equities.command(name="show")
def equities_show():
    """📈 Show equities positions (Robinhood) and total equity

    Fetches live positions via Robinhood (if configured) and displays a
    positions table and total equity. This does not persist positions.
    """
    rh_data = get_robinhood_portfolio()
    if not isinstance(rh_data, dict):
        console.print("[yellow]Equities data unavailable.[/yellow]")
        return

    if rh_data.get('error'):
        err = rh_data['error']
        if err == 'robin-stocks not installed':
            console.print("[yellow]robin-stocks not installed. Install with: pip install robin-stocks python-dotenv[/yellow]")
        elif err == 'missing_credentials':
            console.print("[yellow]Missing Robinhood credentials. Set USERNAME, PASSWORD, ACCOUNT_NUMBER in .env or config.json[/yellow]")
        else:
            console.print(f"[red]Error fetching equities: {err}[/red]")
        return

    positions = rh_data.get('positions', [])
    total_equity = float(rh_data.get('total_equity', 0.0))

    if not positions:
        console.print("[yellow]No open Robinhood stock positions found.[/yellow]")
        return

    table = Table(title="Robinhood Positions")
    table.add_column("Symbol", style="cyan")
    table.add_column("Quantity", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Equity", justify="right", style="green")

    for pos in positions:
        table.add_row(
            str(pos.get('symbol', '')),
            f"{float(pos.get('quantity', 0)):,.4f}",
            f"${float(pos.get('price', 0)):,.2f}",
            f"${float(pos.get('equity', 0)):,.2f}"
        )

    table.add_section()
    table.add_row("TOTAL", "", "", f"${total_equity:,.2f}", style="bold")
    console.print(table)


@cli.group()
def cash():
    """💵 Cash management commands"""
    pass


@cash.command(name="show")
def cash_show():
    """Show current cash balance"""
    portfolio = load_portfolio()
    cash_data = portfolio.get('cash', {"balance": 0.0, "currency": "USD"})
    balance = float(cash_data.get('balance', 0.0))
    currency = cash_data.get('currency', 'USD')

    table = Table(title="Cash")
    table.add_column("Currency", style="cyan")
    table.add_column("Balance", justify="right", style="green")
    table.add_row(str(currency), f"${balance:,.2f}")
    console.print(table)


@cash.command(name="update")
@click.option('--add', 'delta', type=float, default=None, help='Amount to add to cash balance')
@click.option('--subtract', 'subtract', type=float, default=None, help='Amount to subtract from cash balance')
def cash_update(delta: float, subtract: float):
    """Update cash balance by adding or subtracting an amount.

    Examples:
      pt cash update --add 500
      pt cash update --subtract 200
    If no flags are provided, prompts for an operation and amount.
    """
    portfolio = load_portfolio()
    if 'cash' not in portfolio:
        portfolio['cash'] = {"balance": 0.0, "currency": "USD"}

    # Interactive prompt if neither provided
    if delta is None and subtract is None:
        op = Prompt.ask("Add or subtract?", choices=["add", "subtract"], default="add")
        amt = click.prompt("Enter amount", type=float)
        change = amt if op == 'add' else -amt
    else:
        change = 0.0
        if delta is not None:
            change += float(delta)
        if subtract is not None:
            change -= float(subtract)

    current = float(portfolio['cash'].get('balance', 0.0))
    new_balance = current + change
    portfolio['cash']['balance'] = new_balance
    save_portfolio(portfolio)
    sign = '+' if change >= 0 else '-'
    console.print(f"[green]✓ Cash updated:[/green] {sign}${abs(change):,.2f} → Balance: ${new_balance:,.2f}")





@cli.command()
def show():
    """📊 Display your complete portfolio overview
    
    View a comprehensive summary of your entire investment portfolio including:
    • Total portfolio value and asset allocation percentages
    • Robinhood stock positions with P&L
    • Cryptocurrency holdings with current prices
    • Hard assets with spot pricing
    • Detailed breakdown of all positions (optional)
    
    This is your main dashboard for tracking investment performance.
    """
    portfolio = load_portfolio()
    # Fetch Robinhood equities (optional, won’t break if unavailable)
    rh_data = get_robinhood_portfolio()
    rh_total = float(rh_data.get('total_equity', 0.0)) if isinstance(rh_data, dict) else 0.0
    cash_data = portfolio.get('cash', {"balance": 0.0})
    cash_value = float(cash_data.get('balance', 0.0))
    
    console.print(Panel.fit("🔥 Portfolio Overview", style="bold blue"))
    
    # Calculate values
    total_value = 0

    crypto_value = sum(holding.get('quantity', 0) * holding.get('current_price', 0) 
                      for holding in portfolio.get('crypto', {}).get('holdings', []))
    metals_value = sum(convert_to_ounces(asset.get('quantity', 0), asset.get('unit', 'oz')) * asset.get('current_spot_price', 0)
                      for asset in portfolio.get('hard_assets', {}).get('precious_metals', []))
    other_value = sum(asset.get('quantity', 0) * asset.get('current_spot_price', 0) 
                     for asset in portfolio.get('hard_assets', {}).get('other', []))
    hard_assets_value = metals_value + other_value
    total_value = crypto_value + hard_assets_value + rh_total + cash_value
    
    # Create summary table
    table = Table(title="Portfolio Summary")
    table.add_column("Asset Type", style="cyan")
    table.add_column("Holdings", justify="right")
    table.add_column("Value", justify="right", style="green")
    table.add_column("Allocation", justify="right")
    
    if total_value > 0:
        rows = []
        if rh_total > 0:
            rows.append((
                "Robinhood",
                str(len(rh_data.get('positions', [])) if isinstance(rh_data, dict) else 0),
                rh_total,
            ))

        if cash_value > 0:
            rows.append((
                "Cash",
                "1",
                cash_value,
            ))

        if crypto_value > 0:
            rows.append((
                "Cryptocurrency",
                str(len(portfolio.get('crypto', {}).get('holdings', []))),
                crypto_value,
            ))

        if hard_assets_value > 0:
            total_assets = len(portfolio.get('hard_assets', {}).get('precious_metals', [])) + len(portfolio.get('hard_assets', {}).get('other', []))
            rows.append((
                "Hard Assets",
                str(total_assets),
                hard_assets_value,
            ))

        # Sort by allocation desc (value/total_value)
        rows.sort(key=lambda r: (r[2] / total_value) if total_value else 0, reverse=True)

        for label, count, value in rows:
            table.add_row(
                label,
                count,
                f"${value:,.2f}",
                f"{(value/total_value)*100:.1f}%"
            )

        table.add_section()
        table.add_row("TOTAL", "", f"${total_value:,.2f}", "100.0%", style="bold")

        console.print(table)
        
        # Show detailed breakdown if requested
        if click.confirm("\nShow detailed breakdown?", default=False):
            show_detailed(portfolio, rh_data)
    else:
        console.print("\n[yellow]No portfolio data found. Use commands to add your holdings:[/yellow]")
        console.print("• [cyan]portfolio-tracker crypto add[/cyan] - Add crypto holdings")
        console.print("• [cyan]portfolio-tracker assets add[/cyan] - Add hard assets")



def show_detailed(portfolio, rh_data=None):
    """Show detailed portfolio breakdown"""
    # Cash
    cash_data = portfolio.get('cash', {"balance": 0.0, "currency": "USD"})
    balance = float(cash_data.get('balance', 0.0))
    currency = cash_data.get('currency', 'USD')
    cash_table = Table(title="Cash")
    cash_table.add_column("Currency", style="cyan")
    cash_table.add_column("Balance", justify="right", style="green")
    cash_table.add_row(str(currency), f"${balance:,.2f}")
    console.print(cash_table)
    console.print()
    # Robinhood positions
    if isinstance(rh_data, dict) and rh_data.get('positions'):
        rh_table = Table(title="Robinhood Positions")
        rh_table.add_column("Symbol", style="cyan")
        rh_table.add_column("Quantity", justify="right")
        rh_table.add_column("Price", justify="right")
        rh_table.add_column("Equity", justify="right", style="green")

        for pos in rh_data['positions']:
            rh_table.add_row(
                str(pos.get('symbol', '')),
                f"{float(pos.get('quantity', 0)):,.4f}",
                f"${float(pos.get('price', 0)):,.2f}",
                f"${float(pos.get('equity', 0)):,.2f}"
            )

        rh_total = float(rh_data.get('total_equity', 0))
        rh_table.add_section()
        rh_table.add_row("TOTAL", "", "", f"${rh_total:,.2f}", style="bold")
        console.print(rh_table)
        console.print()
    
    # Crypto holdings
    if portfolio.get('crypto', {}).get('holdings', []):
        crypto_table = Table(title="Cryptocurrency Holdings")
        crypto_table.add_column("Name", style="cyan")
        crypto_table.add_column("Quantity", justify="right")
        crypto_table.add_column("Avg Cost", justify="right")
        crypto_table.add_column("Current Price", justify="right")
        crypto_table.add_column("Value", justify="right", style="green")
        crypto_table.add_column("P&L", justify="right")
        
        for holding in portfolio['crypto']['holdings']:
            value = holding['quantity'] * holding['current_price']
            cost_basis = holding['quantity'] * holding['average_cost']
            pnl = value - cost_basis if cost_basis > 0 else 0
            pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            pnl_color = "green" if pnl >= 0 else "red"
            pnl_text = f"${pnl:,.2f} ({pnl_pct:+.1f}%)" if cost_basis > 0 else "N/A"
            
            crypto_table.add_row(
                holding['name'],
                f"{holding['quantity']:.4f}",
                f"${holding['average_cost']:,.2f}" if holding['average_cost'] > 0 else "N/A",
                f"${holding['current_price']:,.2f}",
                f"${value:,.2f}",
                f"[{pnl_color}]{pnl_text}[/{pnl_color}]" if cost_basis > 0 else "N/A"
            )
        
        console.print("\n")
        console.print(crypto_table)

    # Hard assets
    all_hard_assets = portfolio.get('hard_assets', {}).get('precious_metals', []) + portfolio.get('hard_assets', {}).get('other', [])
    if all_hard_assets:
        assets_table = Table(title="Hard Assets")
        assets_table.add_column("Asset", style="cyan")
        assets_table.add_column("Quantity", justify="right")
        assets_table.add_column("Unit", justify="center")
        assets_table.add_column("Avg Cost", justify="right")
        assets_table.add_column("Spot Price", justify="right")
        assets_table.add_column("Value", justify="right", style="green")
        assets_table.add_column("P&L", justify="right")
        
        for asset in all_hard_assets:
            value = convert_to_ounces(asset['quantity'], asset['unit']) * asset['current_spot_price']
            cost_basis = asset['quantity'] * asset['average_cost']
            pnl = value - cost_basis if cost_basis > 0 else 0
            pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            pnl_color = "green" if pnl >= 0 else "red"
            pnl_text = f"${pnl:,.2f} ({pnl_pct:+.1f}%)" if cost_basis > 0 else "N/A"
            
            assets_table.add_row(
                asset['name'],
                f"{asset['quantity']:.2f}",
                asset['unit'],
                f"${asset['average_cost']:,.2f}" if asset['average_cost'] > 0 else "N/A",
                f"${asset['current_spot_price']:,.2f}",
                f"${value:,.2f}",
                f"[{pnl_color}]{pnl_text}[/{pnl_color}]" if cost_basis > 0 else "N/A"
            )
        
        console.print("\n")
        console.print(assets_table)



@cli.command()
def update():
    """🔄 Update all asset prices across your portfolio
    
    Refreshes prices for all assets in your portfolio:
    • Cryptocurrency prices from CoinGecko
    • Precious metal spot prices
    
    This is a convenient way to update your entire portfolio at once.
    """
    console.print("[yellow]Updating all asset prices...[/yellow]")
    
    # Update crypto prices
    console.print("\n[cyan]Updating crypto prices...[/cyan]")
    os.system(f"python3 {__file__} crypto update")
    
    # Update hard asset prices  
    console.print("\n[cyan]Updating hard asset prices...[/cyan]")
    os.system(f"python3 {__file__} assets update")
    
    console.print("\n[green]✓ All prices updated[/green]")

@cli.command()
def config():
    """⚙️ Configure Portfolio Tracker settings
    
    Manage your portfolio tracker configuration:
    • Display preferences (currency, cost basis)
    • API keys (optional, for enhanced features)
    
    Settings are stored locally and encrypted where appropriate.
    """
    config = load_config()

    while True:
        console.print(Panel.fit("⚙️  Configuration Menu", style="bold blue"))
        console.print("1. Robinhood connection")
        console.print("2. General preferences")
        console.print("3. Back to main menu")
        choice = Prompt.ask("Enter your choice", choices=["1", "2", "3"], default="3")

        if choice == '1':
            config = _configure_robinhood_interactive(config)
        elif choice == '2':
            console.print(Panel.fit("General Preferences", style="bold blue"))
            prefs = (config.get("preferences") or {})
            currency = Prompt.ask("Currency (e.g., USD, EUR)", default=prefs.get("currency", "USD"))
            show_cost_basis = click.confirm("Show cost basis in summaries?", default=prefs.get("show_cost_basis", True))
            update_frequency = click.prompt("Auto-update frequency (seconds)", default=prefs.get("update_frequency", 300), type=int)
            config["preferences"] = {
                "currency": currency,
                "show_cost_basis": bool(show_cost_basis),
                "update_frequency": int(update_frequency),
            }
            save_config(config)
            console.print("[green]✓ Preferences saved[/green]")
        elif choice == '3':
            break


@cli.command()
def interactive():
    """🚀 Start interactive mode
    
    Enter an interactive shell where you can run commands without typing 
    'portfolio-tracker' each time. Just type the command directly.
    
    Example:
        portfolio-tracker interactive
        > show
        > crypto add
        > exit
    """
    console.print(Panel.fit("🔥 Portfolio Tracker - Interactive Mode", style="bold blue"))
    console.print("[green]Welcome to Portfolio Tracker interactive mode![/green]")
    console.print("Type commands without 'portfolio-tracker' prefix. Type 'help' for commands or 'exit' to quit.\n")
    
    while True:
        try:
            # Get command from user
            cmd = Prompt.ask("[bold cyan]portfolio-tracker[/bold cyan]", default="help")
            
            # Handle exit commands
            if cmd.lower() in ['exit', 'quit', 'q']:
                console.print("[green]Goodbye! 👋[/green]")
                break
            
            # Handle help
            if cmd.lower() in ['help', 'h', '?']:
                console.print("\n[bold]Available Commands:[/bold]")
                console.print("• [cyan]show[/cyan] - Display portfolio overview")
                console.print("• [cyan]config[/cyan] - Configure settings")
                console.print("• [cyan]update[/cyan] - Update all prices")
                console.print("• [cyan]crypto add[/cyan] - Add crypto holding")
                console.print("• [cyan]crypto remove[/cyan] - Remove crypto holding")
                console.print("• [cyan]crypto update[/cyan] - Update crypto prices")
                console.print("• [cyan]assets add[/cyan] - Add hard asset")
                console.print("• [cyan]assets remove[/cyan] - Remove hard asset")
                console.print("• [cyan]assets update[/cyan] - Update asset prices")
                console.print("• [cyan]equities show[/cyan] - Show Robinhood positions")
                console.print("• [cyan]cash show[/cyan] - Show cash balance")
                console.print("• [cyan]cash update[/cyan] - Add/subtract cash")
                console.print("• [cyan]commands[/cyan] - Show detailed command help")
                console.print("• [cyan]exit[/cyan] - Exit interactive mode\n")
                continue
            
            # Handle commands alias
            if cmd.lower() == 'commands':
                cmd = 'help-commands'
            
            # Split command into parts
            cmd_parts = cmd.strip().split()
            if not cmd_parts:
                continue
                
            # Execute the command by calling the CLI with the parsed command
            try:
                # Create a new context and invoke the command
                ctx = cli.make_context('portfolio-tracker', cmd_parts)
                cli.invoke(ctx)
            except click.ClickException as e:
                console.print(f"[red]Error: {e.message}[/red]")
            except click.Abort:
                console.print("[yellow]Command cancelled[/yellow]")
            except Exception as e:
                console.print(f"[red]Error executing command: {str(e)}[/red]")
                console.print("[yellow]Type 'help' for available commands[/yellow]")
            
            console.print()  # Add spacing between commands
            
        except KeyboardInterrupt:
            console.print("\n[green]Goodbye! 👋[/green]")
            break
        except EOFError:
            console.print("\n[green]Goodbye! 👋[/green]")
            break

@cli.command()
def help_commands():
    """📚 Show detailed help for all commands
    
    Display a comprehensive overview of all available commands with examples.
    This is more detailed than the standard --help option.
    """
    console.print(Panel.fit("🔥 Portfolio Tracker - Command Reference", style="bold blue"))
    
    # Main commands
    main_table = Table(title="📊 Main Commands")
    main_table.add_column("Command", style="cyan")
    main_table.add_column("Description", style="white")
    main_table.add_column("Example", style="yellow")
    
    main_table.add_row("show", "Display portfolio overview", "portfolio-tracker show")
    main_table.add_row("update", "Update all asset prices", "portfolio-tracker update") 
    main_table.add_row("config", "Configure settings", "portfolio-tracker config")
    
    console.print("\n")
    console.print(main_table)
    
    
    # Crypto commands  
    crypto_table = Table(title="₿ Cryptocurrency Commands")
    crypto_table.add_column("Command", style="cyan")
    crypto_table.add_column("Description", style="white")
    crypto_table.add_column("Example", style="yellow")
    
    crypto_table.add_row("crypto add", "Add crypto holding", "portfolio-tracker crypto add")
    crypto_table.add_row("crypto remove", "Remove crypto holding", "portfolio-tracker crypto remove")
    crypto_table.add_row("crypto update", "Update crypto prices", "portfolio-tracker crypto update")
    
    console.print("\n") 
    console.print(crypto_table)
    
    # Assets commands
    assets_table = Table(title="🥇 Hard Assets Commands")
    assets_table.add_column("Command", style="cyan")
    assets_table.add_column("Description", style="white")
    assets_table.add_column("Example", style="yellow")
    
    assets_table.add_row("assets add", "Add hard asset", "portfolio-tracker assets add")
    assets_table.add_row("assets remove", "Remove hard asset", "portfolio-tracker assets remove")
    assets_table.add_row("assets update", "Update asset prices", "portfolio-tracker assets update")
    
    console.print("\n")
    console.print(assets_table)

    # Equities commands
    equities_table = Table(title="📈 Equities Commands")
    equities_table.add_column("Command", style="cyan")
    equities_table.add_column("Description", style="white")
    equities_table.add_column("Example", style="yellow")

    equities_table.add_row("equities show", "Show Robinhood positions", "portfolio-tracker equities show")
    
    console.print("\n")
    console.print(equities_table)

    # Cash commands
    cash_table = Table(title="💵 Cash Commands")
    cash_table.add_column("Command", style="cyan")
    cash_table.add_column("Description", style="white")
    cash_table.add_column("Example", style="yellow")

    cash_table.add_row("cash show", "Show cash balance", "portfolio-tracker cash show")
    cash_table.add_row("cash update", "Add/subtract cash balance", "portfolio-tracker cash update --add 100")

    console.print("\n")
    console.print(cash_table)
    
    console.print("\n")
    console.print("[bold green]💡 Pro Tips:[/bold green]")
    console.print("• Use 'pt' as a shortcut instead of 'portfolio-tracker'")
    console.print("• Add '--help' to any command for detailed options")
    console.print("• Run 'pt show' regularly to track your portfolio performance")
    console.print("• Use 'pt update' to refresh all prices at once")

if __name__ == '__main__':
    cli()
