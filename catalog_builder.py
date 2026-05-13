#!/usr/bin/env python3
"""
Catalog Builder - Interactive Interface for Product Catalog Automation

This script provides an easy-to-use interface for the complete product catalog
automation workflow:

1. Extract images and metadata from PDF catalogs
2. Review and label images with corrected metadata
3. Upload to Google Drive and generate Excel with AI descriptions

Usage: python catalog_builder.py
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def clear_screen():
    """Clear the terminal screen."""
    if sys.platform == "win32":
        os.system("cls")
    else:
        os.system("clear")


def print_header():
    """Print the main header."""
    print("=" * 70)
    print("🏗️  PRODUCT CATALOG BUILDER")
    print("=" * 70)
    print("Automated PDF extraction → Review → Google Drive upload")
    print("=" * 70)


def print_menu():
    """Print the main menu."""
    print("\n📋 AVAILABLE OPERATIONS:")
    print("  1. 📄 Extract images and metadata from PDF(s)")
    print("  2. 🔍 Review and label images (interactive)")
    print("  3. ☁️  Upload to Drive & generate Excel")
    print("  4. 🔧 Check system requirements")
    print("  5. 📖 Show setup instructions")
    print("  6. 📂 Open output folders")
    print("  7. 🧹 Clean temporary files")
    print("  0. Exit")
    print("-" * 70)


def check_requirements():
    """Check if all required dependencies are installed."""
    print("\n🔍 CHECKING SYSTEM REQUIREMENTS...")

    requirements = [
        ("Python 3.6+", sys.version_info >= (3, 6)),
        ("fitz (PyMuPDF)", True),  # Will check import
        ("PIL (Pillow)", True),    # Will check import
        ("pandas", True),          # Will check import
        ("requests", True),        # Will check import
        ("Google API client", True), # Will check import
        ("tkinter", True),         # Will check import
    ]

    missing = []
    for req, status in requirements:
        if req == "fitz (PyMuPDF)":
            try:
                import fitz
                print(f"  ✅ {req}")
            except ImportError:
                print(f"  ❌ {req} - MISSING")
                missing.append("fitz")
        elif req == "PIL (Pillow)":
            try:
                import PIL
                print(f"  ✅ {req}")
            except ImportError:
                print(f"  ❌ {req} - MISSING")
                missing.append("Pillow")
        elif req == "pandas":
            try:
                import pandas
                print(f"  ✅ {req}")
            except ImportError:
                print(f"  ❌ {req} - MISSING")
                missing.append("pandas")
        elif req == "requests":
            try:
                import requests
                print(f"  ✅ {req}")
            except ImportError:
                print(f"  ❌ {req} - MISSING")
                missing.append("requests")
        elif req == "Google API client":
            try:
                import googleapiclient
                print(f"  ✅ {req}")
            except ImportError:
                print(f"  ❌ {req} - MISSING")
                missing.append("google-api-python-client")
        elif req == "tkinter":
            try:
                import tkinter
                print(f"  ✅ {req}")
            except ImportError:
                print(f"  ❌ {req} - MISSING (built-in on most systems)")
        else:
            if status:
                print(f"  ✅ {req}")
            else:
                print(f"  ❌ {req}")
                missing.append(req)

    if missing:
        print(f"\n⚠️  MISSING DEPENDENCIES: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False

    print("\n✅ All basic requirements satisfied!")
    return True


def check_ollama():
    """Check if Ollama is running and has required models."""
    print("\n🤖 CHECKING OLLAMA SETUP...")

    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]

            if "llava" in model_names:
                print("  ✅ Ollama running with llava model")
                return True
            else:
                print("  ⚠️  Ollama running but llava model not found")
                print("  Run: ollama pull llava")
                return False
        else:
            print("  ❌ Ollama API not responding")
            return False
    except Exception as e:
        print(f"  ❌ Ollama not running: {e}")
        print("  Start Ollama: ollama serve")
        return False


def check_google_drive():
    """Check Google Drive setup."""
    print("\n☁️  CHECKING GOOGLE DRIVE SETUP...")

    creds_path = Path("credentials.json")
    if creds_path.exists():
        print("  ✅ credentials.json found")
    else:
        print("  ❌ credentials.json missing")
        print("  Download from Google Cloud Console")
        return False

    # Check if token exists
    token_path = Path("token.pickle")
    if token_path.exists():
        print("  ✅ token.pickle found (authenticated)")
    else:
        print("  ⚠️  token.pickle missing (will authenticate on first run)")

    # Check folder ID in script or environment
    script_path = Path("3_upload_and_excel.py")
    env_drive_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if env_drive_id:
        print("  ✅ GOOGLE_DRIVE_FOLDER_ID set via environment variable")
    elif script_path.exists():
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
            if "YOUR_GOOGLE_DRIVE_FOLDER_ID_HERE" in content:
                print("  ❌ GOOGLE_DRIVE_FOLDER_ID not set in 3_upload_and_excel.py")
                return False
            else:
                print("  ✅ GOOGLE_DRIVE_FOLDER_ID configured in script")
    else:
        print("  ❌ 3_upload_and_excel.py not found")
        return False

    return True


def run_step(step_number, step_name, script_name):
    """Run a specific step script."""
    print(f"\n🚀 RUNNING STEP {step_number}: {step_name}")
    print("-" * 70)

    script_path = Path(script_name)
    if not script_path.exists():
        print(f"❌ Script not found: {script_name}")
        input("\nPress Enter to continue...")
        return

    try:
        # Run the script
        result = subprocess.run([sys.executable, str(script_path)],
                              cwd=os.getcwd(),
                              capture_output=False,
                              text=True)

        if result.returncode == 0:
            print(f"\n✅ STEP {step_number} COMPLETED SUCCESSFULLY!")
        else:
            print(f"\n❌ STEP {step_number} FAILED (exit code: {result.returncode})")

    except KeyboardInterrupt:
        print(f"\n⚠️  STEP {step_number} INTERRUPTED BY USER")
    except Exception as e:
        print(f"\n❌ ERROR RUNNING STEP {step_number}: {e}")

    input("\nPress Enter to continue...")


def show_setup_instructions():
    """Show setup instructions."""
    print("\n📖 SETUP INSTRUCTIONS")
    print("=" * 70)

    print("\n1. INSTALL DEPENDENCIES:")
    print("   pip install -r requirements.txt")

    print("\n2. GOOGLE DRIVE SETUP:")
    print("   a. Create Google Cloud project")
    print("   b. Enable Google Drive API")
    print("   c. Create OAuth 2.0 credentials")
    print("   d. Download credentials.json")
    print("   e. Set GOOGLE_DRIVE_FOLDER_ID in 3_upload_and_excel.py")

    print("\n3. OLLAMA SETUP:")
    print("   a. Install Ollama: https://ollama.ai")
    print("   b. Pull llava model: ollama pull llava")
    print("   c. Start Ollama: ollama serve")

    print("\n4. WORKFLOW:")
    print("   Step 1: Extract from PDF → creates extracted_text/ and extracted_images/")
    print("   Step 2: Review TXT files → creates corrected_metadata.txt and labelled_images/")
    print("   Step 3: Upload to Drive → creates product_catalog.xlsx and image_links.txt")

    input("\nPress Enter to continue...")


def open_output_folders():
    """Open the main output folders."""
    print("\n📂 OPENING OUTPUT FOLDERS...")

    folders = [
        ("extracted_images", "Extracted product images"),
        ("extracted_text", "Metadata text files for review"),
        ("labelled_images", "Labelled images with SKU"),
    ]

    for folder_name, description in folders:
        folder_path = Path(folder_name)
        if folder_path.exists():
            print(f"  📁 {description}: {folder_path}")
            if sys.platform == "win32":
                os.startfile(str(folder_path))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(folder_path)])
            else:
                subprocess.run(["xdg-open", str(folder_path)])
        else:
            print(f"  📁 {description}: {folder_name} (not created yet)")

    input("\nPress Enter to continue...")


def clean_temporary_files():
    """Clean temporary files."""
    print("\n🧹 CLEANING TEMPORARY FILES...")

    temp_files = [
        "extracted_data.csv",
        "corrected_metadata.txt",
        "image_links.txt",
        "product_catalog.xlsx",
        "token.pickle",
    ]

    cleaned = 0
    for filename in temp_files:
        file_path = Path(filename)
        if file_path.exists():
            file_path.unlink()
            print(f"  🗑️  Removed: {filename}")
            cleaned += 1

    if cleaned == 0:
        print("  ✅ No temporary files to clean")
    else:
        print(f"  ✅ Cleaned {cleaned} temporary files")

    input("\nPress Enter to continue...")


def check_workflow_status():
    """Check the current status of the workflow."""
    print("\n📊 WORKFLOW STATUS")
    print("-" * 70)

    status_items = [
        ("PDF extraction", "extracted_text", "extracted_images"),
        ("Image review", "corrected_metadata.txt", "labelled_images"),
        ("Drive upload", "product_catalog.xlsx", "image_links.txt"),
    ]

    for step, *files in status_items:
        all_exist = all(Path(f).exists() for f in files)
        status = "✅ COMPLETED" if all_exist else "⏳ PENDING"
        print(f"  {step}: {status}")

    print("\n📁 FOLDER STATUS:")
    folders = ["extracted_images", "extracted_text", "labelled_images"]
    for folder in folders:
        exists = Path(folder).exists()
        status = "✅ EXISTS" if exists else "❌ MISSING"
        print(f"  {folder}/: {status}")


def main():
    """Main interface loop."""
    while True:
        clear_screen()
        print_header()
        check_workflow_status()
        print_menu()

        try:
            choice = input("Enter your choice (0-7): ").strip()

            if choice == "0":
                print("\n👋 Goodbye!")
                break
            elif choice == "1":
                run_step(1, "Extract images and metadata from PDF(s)", "1_extract_from_pdf.py")
            elif choice == "2":
                run_step(2, "Review and label images (interactive)", "2_review_and_label.py")
            elif choice == "3":
                run_step(3, "Upload to Drive & generate Excel", "3_upload_and_excel.py")
            elif choice == "4":
                check_requirements()
                check_ollama()
                check_google_drive()
                input("\nPress Enter to continue...")
            elif choice == "5":
                show_setup_instructions()
            elif choice == "6":
                open_output_folders()
            elif choice == "7":
                clean_temporary_files()
            else:
                print("\n❌ Invalid choice. Please enter 0-7.")
                input("Press Enter to continue...")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            input("Press Enter to continue...")


if __name__ == "__main__":
    main()