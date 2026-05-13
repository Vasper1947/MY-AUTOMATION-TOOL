@echo off
REM Setup script for Product Catalog Automation Tool (Windows)
REM Run this script after cloning the repository

echo === PRODUCT CATALOG AUTOMATION SETUP ===
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8+ first.
    pause
    exit /b 1
)

echo ✅ Python found:
python --version
echo.

REM Create virtual environment
echo Creating virtual environment...
python -m venv .venv

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Setup .env file
echo.
echo Setting up configuration...
if not exist .env (
    copy .env.example .env
    echo ✅ Created .env file from template
    echo ⚠️  Please edit .env file with your API keys and settings
) else (
    echo ✅ .env file already exists
)

echo.
echo === SETUP COMPLETE ===
echo.
echo To run the automation tool:
echo 1. Activate environment: .venv\Scripts\activate
echo 2. Run interactive menu: python catalog_builder.py
echo.
echo Or run individual steps:
echo python 1_extract_from_pdf.py
echo python 2_review_and_label.py
echo python 3_upload_and_excel.py
echo.
echo Happy automating! 🚀
echo.
pause