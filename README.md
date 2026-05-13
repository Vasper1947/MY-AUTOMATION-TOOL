# 📦 Product Catalog Automation System

A fully modular, highly interactive system for extracting product images and metadata from PDF catalogs, labeling them with SKUs, uploading to Google Drive, and generating an Excel spreadsheet with AI-powered product descriptions.

---

## 🎯 System Overview

### Three-Step Workflow

**Step 1: Extract Images from PDF**
- Reads all PDFs in a folder
- Extracts product images named by their SKU
- Automatically detects SKU, brand, finish, dimensions below each image
- Saves images to `extracted_images/` folder
- Creates `extracted_data.csv` with all metadata

**Step 2: Review & Label Images**
- Opens each image for visual inspection
- Allows you to **verify or correct** all fields (SKU, brand, finish, dimensions, description)
- Does NOT assume missing fields - asks you to provide them
- Labels images with SKU text in the corner
- Saves labeled images to `labelled_images/`
- Creates `extracted_data_corrected.csv` with final metadata

**Step 3: Upload & Generate Excel**
- Authenticates with Google Drive (one-time setup)
- Generates **AI-powered product descriptions** using Ollama vision
  - Analyzes the actual product IMAGE
  - Writes professional e-commerce descriptions
  - Precision-focused for building materials/products
- Uploads all labeled images to Google Drive
- Creates **direct shareable links** for each image
- Generates `product_catalog.xlsx` with:
  - SKU, Brand, Finish, Dimensions
  - AI Description (image-based)
  - Direct Google Drive link to each image
- Uploads Excel file to Google Drive

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Drive Setup (One-Time)

1. **Create a Google Cloud project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Drive API

2. **Create OAuth credentials:**
   - Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
   - Choose "Desktop application"
   - Download the JSON file and save as `credentials.json` in your automation folder

3. **Create a Google Drive folder:**
   - Create a new folder in your Google Drive
   - Copy the folder ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
   - Edit **`3_upload_and_excel.py`** and update:
     ```python
     GOOGLE_DRIVE_FOLDER_ID = "YOUR_GOOGLE_DRIVE_FOLDER_ID_HERE"  # ← Paste here
     ```

### 3. Setup Ollama (For AI Descriptions)

**Local Installation (Recommended):**
```bash
# Download from https://ollama.ai
# Run Ollama and pull the vision model
ollama pull llava
# Keep Ollama running in the background
ollama serve
```

**Or set custom Ollama URL:**
```bash
set OLLAMA_URL=http://your-ollama-server:11434/api/generate
set OLLAMA_MODEL=llava  # or your vision model
```

---

## 🎮 Interactive Build Interface

**NEW!** For easy access to all features, use the interactive catalog builder:

```bash
python catalog_builder.py
```

**Or double-click:** `run_catalog.bat` (Windows)

**Features:**
- 📋 **Menu-driven interface** - No need to remember script names
- 🔍 **System checks** - Validates Ollama, Google Drive, and dependencies
- 📊 **Workflow status** - Shows completion status of each step
- 📂 **Folder management** - Open output folders with one click
- 🧹 **Cleanup tools** - Remove temporary files easily
- 📖 **Built-in help** - Setup instructions and troubleshooting

**Menu Options:**
1. 📄 Extract images and metadata from PDF(s)
2. 🔍 Review and label images (interactive)
3. ☁️ Upload to Drive & generate Excel
4. 🔧 Check system requirements
5. 📖 Show setup instructions
6. 📂 Open output folders
7. 🧹 Clean temporary files
0. Exit

---

## 📋 Step-by-Step Usage (Manual)

### Step 1: Extract Images

```bash
python 1_extract_from_pdf.py
```

**What happens:**
1. Select PDF file or folder containing PDFs
2. Script scans all PDFs for images
3. For each image, it looks for text below it (SKU, brand, finish, dimensions, description)
4. If SKU is not found clearly, you'll be asked to provide it
5. Images are saved as `{SKU}.png` in `extracted_images/`
6. CSV file is created with all extracted data

**Output:**
- `extracted_images/` folder with images named by SKU
- `extracted_data.csv` with metadata

---

### Step 2: Review & Label Images

```bash
python 2_review_and_label.py
```

**What happens:**
1. Select the `extracted_data.csv` file
2. For each image:
   - Image opens in your default viewer
   - You can see and verify/correct:
     - **SKU** (required)
     - **Brand** (optional)
     - **Finish** (optional)
     - **Dimensions** (optional)
     - **Description** (optional)
   - Labeled image is saved with SKU in corner
3. Continue or stop at any time
4. Updated CSV saved as `extracted_data_corrected.csv`

**Features:**
- Press Enter to keep current value
- Type new value to overwrite
- Leave blank to skip optional fields
- Pause between images

**Output:**
- `labelled_images/` folder with labeled product images
- `extracted_data_corrected.csv` with verified metadata

---

### Step 3: Upload & Create Excel

```bash
python 3_upload_and_excel.py
```

**What happens:**
1. Reads the corrected CSV file
2. **Generates AI descriptions:**
   - Ollama analyzes each product image
   - Creates professional e-commerce description (2-3 sentences)
   - Focuses on visual features, materials, dimensions
   - Uses precise, persuasive language
3. Authenticates with Google Drive (first run opens browser for OAuth)
4. Uploads each labeled image to Google Drive
5. Makes images publicly viewable and creates direct links
6. Optionally applies custom Excel template
7. Generates `product_catalog.xlsx` with all product details and image links
8. Uploads Excel file to Google Drive

**Prompts:**
- AI Description generation toggle
- Option to use custom Excel template

**Output:**
- `product_catalog.xlsx` with:
  - SKU, Brand, Finish, Dimensions
  - AI-Generated Description
  - Direct Google Drive image link
- All images and Excel uploaded to Google Drive
- `token.pickle` (stores auth token for future use)

---

## ⚙️ Configuration

### Hardcoded Google Drive Settings

Edit `3_upload_and_excel.py`:

```python
GOOGLE_DRIVE_FOLDER_ID = "YOUR_GOOGLE_DRIVE_FOLDER_ID_HERE"  # Update this
CREDENTIALS_PATH = "credentials.json"  # Path relative to script
```

### Ollama Settings

Set environment variables or edit the script:

```python
OLLAMA_URL = "http://localhost:11434/api/generate"  # Default
OLLAMA_MODEL = "llava"  # Vision-capable model
```

### Custom Excel Template

In Step 3, you can select a custom Excel template (`.xlsx`) to use as the output format instead of the default table.

---

## 📝 CSV Format

### `extracted_data.csv` (Step 1 output)

| Field | Description |
|-------|-------------|
| page | PDF page number |
| image_index | Image index on page |
| image_file | Filename of extracted image (PNG) |
| image_path | Full path to extracted image |
| sku | Product SKU |
| brand | Product brand (may be empty) |
| finish | Surface finish type (may be empty) |
| dimensions | Product dimensions (may be empty) |
| original_desc | Original description text (may be empty) |

### `extracted_data_corrected.csv` (Step 2 output)

Same as above, plus:
- Verified/corrected values for all fields
- `labelled_image_path`: Path to labeled image with SKU drawn on it

---

## 🖼️ File Structure

```
MY AUTOMATION/
├── 1_extract_from_pdf.py          # Step 1: Extract images & metadata
├── 2_review_and_label.py           # Step 2: Review & label
├── 3_upload_and_excel.py           # Step 3: Upload & create Excel
├── requirements.txt                 # Python dependencies
├── credentials.json                 # Google OAuth (create manually)
├── token.pickle                     # Google auth token (auto-created)
├── *.pdf                            # Your PDF catalogs
├── extracted_images/                # Raw images from PDF (created by Step 1)
├── labelled_images/                 # Images with SKU labels (created by Step 2)
├── extracted_data.csv               # Step 1 output
├── extracted_data_corrected.csv     # Step 2 output
└── product_catalog.xlsx             # Step 3 output
```

---

## 🔧 Troubleshooting

### "No PDF files found"
- Make sure PDF files are in the same folder as the scripts
- Or provide the correct folder path when prompted

### "Could not find extracted_data.csv"
- Run Step 1 first
- Make sure `extracted_data.csv` is in the correct folder

### Ollama not responding
- Make sure Ollama is running: `ollama serve`
- Check URL and model: `set OLLAMA_URL=...` and `set OLLAMA_MODEL=...`
- Or set in environment variables

### Google Drive authentication fails
- Check that `credentials.json` exists in the automation folder
- Delete `token.pickle` to force re-authentication
- Ensure your Google Drive folder ID is correct in the script

### Image won't open in Step 2
- Check that the image path is correct
- Make sure your default image viewer is working
- Images may need to be in a supported format (PNG, JPG)

### Unicode/emoji errors
- Ensure your terminal supports UTF-8 encoding
- On Windows: Add `chcp 65001` before running Python

---

## 🎨 E-Commerce Description Generation

The AI description generation uses Ollama's vision capabilities to:

✅ **Analyze the actual product image**
- Detects materials, colors, finish textures
- Identifies dimensions and proportions
- Notes any visible features or design elements

✅ **Generate professional descriptions**
- 2-3 sentences, optimized for e-commerce
- Focus on visual appeal and material quality
- Include dimensions and finish when visible
- Persuasive, specific language
- No generic descriptions

✅ **Tailored for building materials**
- Emphasis on durability, finish quality
- Professional tone for B2B/construction context
- Precise specifications

---

## 🔒 Privacy & Security

- **Credentials:** `credentials.json` gives access to your Google Drive. Keep it secure.
- **Token:** `token.pickle` stores the authentication token. Delete it to revoke access.
- **Images:** Made public on Google Drive for sharing links. Control access via folder permissions.

---

## 📞 Support

Check the output of each script for detailed error messages and next steps.

---

**Happy cataloging! 🎉**
