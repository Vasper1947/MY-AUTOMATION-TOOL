#!/bin/bash
# Setup script for Product Catalog Automation Tool
# Run this script after cloning the repository

echo "=== PRODUCT CATALOG AUTOMATION SETUP ==="
echo ""

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✅ Python found: $(python --version)"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Setup .env file
echo ""
echo "Setting up configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo "⚠️  Please edit .env file with your API keys and settings"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "=== SETUP COMPLETE ==="
echo ""
echo "To run the automation tool:"
echo "1. Activate environment: source .venv/bin/activate"
echo "2. Run interactive menu: python catalog_builder.py"
echo ""
echo "Or run individual steps:"
echo "python 1_extract_from_pdf.py"
echo "python 2_review_and_label.py"
echo "python 3_upload_and_excel.py"
echo ""
echo "Happy automating! 🚀"