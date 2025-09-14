#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from portfolio_tracker import get_crypto_price, get_metals_price
from rich.console import Console

console = Console()

def test_crypto_prices():
    console.print("\n🧪 Testing Crypto Price APIs")
    console.print("=" * 40)
    
    # Test Bitcoin
    console.print("[yellow]Fetching Bitcoin price...[/yellow]")
    btc_price = get_crypto_price("bitcoin")
    if btc_price:
        console.print(f"[green]✓ Bitcoin: ${btc_price:,.2f}[/green]")
    else:
        console.print("[red]✗ Failed to fetch Bitcoin price[/red]")
    
    # Test Ethereum  
    console.print("[yellow]Fetching Ethereum price...[/yellow]")
    eth_price = get_crypto_price("ethereum")
    if eth_price:
        console.print(f"[green]✓ Ethereum: ${eth_price:,.2f}[/green]")
    else:
        console.print("[red]✗ Failed to fetch Ethereum price[/red]")

def test_metals_prices():
    console.print("\n🥇 Testing Metals Price APIs")
    console.print("=" * 40)
    
    metals = ['gold', 'silver', 'platinum', 'palladium']
    
    for metal in metals:
        console.print(f"[yellow]Fetching {metal.title()} price...[/yellow]")
        price = get_metals_price(metal)
        if price:
            console.print(f"[green]✓ {metal.title()}: ${price:,.2f}/oz[/green]")
        else:
            console.print(f"[red]✗ Failed to fetch {metal} price[/red]")

if __name__ == "__main__":
    console.print("🔍 Portfolio Tracker - Price API Testing")
    console.print("=" * 50)
    
    test_crypto_prices()
    test_metals_prices()
    
    console.print("\n🎉 Price API testing complete!")