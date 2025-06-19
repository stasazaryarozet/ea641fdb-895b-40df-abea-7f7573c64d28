#!/bin/bash
# Installation script for Tilda Migration Agent

set -e

echo "🚀 Installing Tilda to Google Cloud Migration Agent..."

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8+ is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Install the package
echo "🔧 Installing package..."
pip install -e .

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p extracted_data
mkdir -p form_handler

# Copy configuration example
if [ ! -f config.yaml ]; then
    echo "📋 Copying configuration example..."
    cp config.example.yaml config.yaml
    echo "⚠️ Please edit config.yaml with your settings before running the agent"
fi

# Check Google Cloud SDK
if ! command -v gcloud &> /dev/null; then
    echo "⚠️ Google Cloud SDK not found. Please install it:"
    echo "   https://cloud.google.com/sdk/docs/install"
else
    echo "✅ Google Cloud SDK found"
fi

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your settings"
echo "2. Set up Google Cloud credentials"
echo "3. Run: python src/main.py validate"
echo "4. Run: python src/main.py migrate"
echo ""
echo "For more information, see docs/README.md" 