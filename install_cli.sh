#!/bin/bash

echo "🔥 Portfolio Tracker CLI Installation"
echo "====================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3 first: https://python.org"
    exit 1
fi

echo "✅ Python 3 found"

# Check if pip is installed
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "❌ pip is required but not installed."
    echo "Please install pip first"
    exit 1
fi

echo "✅ pip found"

# Install in development mode (editable)
echo "📦 Installing Portfolio Tracker CLI..."
pip3 install -e .

if [ $? -eq 0 ]; then
    echo "✅ Portfolio Tracker CLI installed successfully!"
    echo ""
    echo "🎉 You can now use these commands:"
    echo "   portfolio-tracker --help           # Show all available commands"
    echo "   portfolio-tracker show             # View your portfolio"  
    echo "   portfolio-tracker config           # Configure settings"
    echo "   portfolio-tracker crypto add       # Add crypto holdings"
    echo "   portfolio-tracker assets add       # Add hard assets"
    echo ""
    echo "🔗 Short alias available: 'pt' (same as portfolio-tracker)"
    echo "   pt show              # Quick portfolio view"
    echo "   pt update            # Update all prices"
    echo ""
    echo "📚 For detailed help on any command:"
    echo "   portfolio-tracker COMMAND --help"
    echo ""
    echo "🚀 Quick start: portfolio-tracker config"
else
    echo "❌ Installation failed"
    echo "Try running: pip3 install --user -e ."
    exit 1
fi