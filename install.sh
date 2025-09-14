#!/bin/bash

echo "🔥 Portfolio Tracker Installation"
echo "=================================="

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

# Create virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv venv

if [ $? -eq 0 ]; then
    echo "✅ Virtual environment created"
else
    echo "❌ Failed to create virtual environment"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate && pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Make script executable
chmod +x portfolio_tracker.py
echo "✅ Made portfolio_tracker.py executable"

# Create alias suggestion
echo ""
echo "🎉 Installation complete!"
echo ""
echo "Quick start:"
echo "  python3 portfolio_tracker.py config    # Configure settings"
echo "  python3 portfolio_tracker.py show      # View portfolio"
echo ""
echo "💡 Pro tip: Create an alias for easier use:"
echo "  echo 'alias pt=\"cd $(pwd) && source venv/bin/activate && python portfolio_tracker.py\"' >> ~/.bashrc"
echo "  source ~/.bashrc"
echo "  pt show  # Now you can use 'pt' instead"
echo ""
echo "Or run directly:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python portfolio_tracker.py show"
echo ""
echo "📚 See README.md for full documentation"