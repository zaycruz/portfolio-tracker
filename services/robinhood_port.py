"""
Robinhood portfolio integration helpers.

This module provides safe, importable functions for fetching live Robinhood
positions and summarizing their equity. All heavy dependencies are imported
inside functions to avoid ImportError when the feature isn't used.

Expected credentials (one of):
- Environment variables: USERNAME, PASSWORD, ACCOUNT_NUMBER
- Config dict passed to get_portfolio_data with keys under 'robinhood'

Returns lightweight dicts to be consumed by the CLI without persisting
credentials or positions to disk.
"""

from typing import Any, Dict, List, Optional
import os


def _load_env_credentials() -> Dict[str, Optional[str]]:
    """Load credentials from .env/env vars if available.

    Attempts to import python-dotenv, but falls back gracefully if missing.
    """
    try:
        # Optional dependency
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except Exception:
        # If dotenv isn't installed, rely purely on the environment
        pass

    return {
        "username": os.getenv("USERNAME"),
        "password": os.getenv("PASSWORD"),
        "account_number": os.getenv("ACCOUNT_NUMBER"),
    }


def _ensure_robinhood():
    """Import robin_stocks.robinhood safely, returning the module or None."""
    try:
        import robin_stocks.robinhood as r  # type: ignore
        return r
    except Exception:
        return None


def get_portfolio_data(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fetch open stock positions and total equity from Robinhood.

    Args:
        config: Optional config dict which may contain a 'robinhood' section
                with 'username', 'password', and 'account_number'.

    Returns:
        {
          'positions': [
             { 'symbol': str, 'quantity': float, 'price': float, 'equity': float }
          ],
          'total_equity': float,
          'error': Optional[str]
        }
    """
    r = _ensure_robinhood()
    if r is None:
        return {"positions": [], "total_equity": 0.0, "error": "robin-stocks not installed"}

    creds = {"username": None, "password": None, "account_number": None}
    if config and isinstance(config, dict):
        rh_cfg = (config.get("robinhood") or {})
        creds.update({
            "username": rh_cfg.get("username"),
            "password": rh_cfg.get("password"),
            "account_number": rh_cfg.get("account_number"),
        })

    # Fallback to env/.env
    env_creds = _load_env_credentials()
    for k, v in env_creds.items():
        if not creds.get(k):
            creds[k] = v

    if not all([creds.get("username"), creds.get("password"), creds.get("account_number")]):
        return {"positions": [], "total_equity": 0.0, "error": "missing_credentials"}

    try:
        r.login(creds["username"], creds["password"])  # type: ignore[arg-type]
        positions = r.account.get_open_stock_positions(account_number=creds["account_number"])  # type: ignore[index]
    except Exception as e:
        return {"positions": [], "total_equity": 0.0, "error": f"login_or_fetch_failed: {e}"}

    total_equity = 0.0
    normalized: List[Dict[str, Any]] = []

    try:
        for p in positions:
            try:
                symbol = r.get_symbol_by_url(p["instrument"])  # type: ignore[index]
                qty = float(p.get("quantity", 0))
                latest = r.stocks.get_latest_price(symbol, includeExtendedHours=True)[0]
                price = float(latest)
                equity = qty * price
                total_equity += equity
                normalized.append({
                    "symbol": symbol,
                    "quantity": qty,
                    "price": price,
                    "equity": equity,
                })
            except Exception:
                # Skip malformed position entries safely
                continue
    finally:
        try:
            r.logout()
        except Exception:
            pass

    return {"positions": normalized, "total_equity": total_equity, "error": None}
