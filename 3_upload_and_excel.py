#!/usr/bin/env python3
"""
Step 3: Upload labelled images to Google Drive and create Excel with AI descriptions.
Uses Ollama for vision-based product descriptions with e-commerce focus.
Supports custom Excel template.
HARDCODED: Google Drive folder ID and credentials path.
"""

import os
import pickle
import base64
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ========== HARDCODED GOOGLE DRIVE SETTINGS ==========
GOOGLE_DRIVE_FOLDER_ID = "YOUR_GOOGLE_DRIVE_FOLDER_ID_HERE"  # CHANGE THIS
CREDENTIALS_PATH = "credentials.json"  # Must be in same directory as script
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# ========== OLLAMA SETTINGS (Vision-capable model) ==========
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llava")  # Vision-capable model

ECOMMERCE_PROMPT_TEMPLATE = """You are a professional e-commerce product description writer specializing in building materials.
Based on the product image provided, generate a compelling, accurate product description for {sku}.
{metadata_context}

Requirements:
- 2-3 sentences maximum
- Focus on visual features, material quality, and durability
- Mention dimensions if visible
- Include finish type if applicable
- Use professional, persuasive language
- No HTML or markdown formatting
- Be specific and avoid generic descriptions

Generate the description now:"""


def choose_txt_file():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(title="Select corrected metadata TXT file", filetypes=[("Text files", "*.txt")])
        root.destroy()
        return path
    except Exception:
        return ""


def choose_excel_template():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(title="Select Excel template (optional)", filetypes=[("Excel files", "*.xlsx")])
        root.destroy()
        return path
    except Exception:
        return ""


def get_template_path_from_config(base_dir):
    """Try to read template path from config created by Step 1."""
    config_path = Path(base_dir) / "template_config.txt"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("EXCEL_TEMPLATE_PATH="):
                        path_str = line.split("=", 1)[1].strip()
                        if Path(path_str).exists():
                            return path_str
        except Exception:
            pass
    return None


def authenticate_drive(base_dir: Path):
    """Authenticate with Google Drive using hardcoded credentials path."""
    creds = None
    token_path = base_dir / "token.pickle"
    credentials_path = base_dir / CREDENTIALS_PATH

    if token_path.exists():
        with open(token_path, "rb") as token_file:
            creds = pickle.load(token_file)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"🔴 {CREDENTIALS_PATH} not found in {base_dir}\n"
                    "Download from Google Cloud Console and place here."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as token_file:
            pickle.dump(creds, token_file)

    return build("drive", "v3", credentials=creds)


def make_public(service, file_id):
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
        supportsAllDrives=True,
        fields="id"
    ).execute()


def create_drive_folder(service, parent_id: str, folder_name: str) -> str:
    """Create or return a folder in Google Drive under the parent folder."""
    query = (
        f"mimeType='application/vnd.google-apps.folder' "
        f"and name='{folder_name}' and '{parent_id}' in parents "
        "and trashed=false"
    )
    response = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = response.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    folder = service.files().create(body=metadata, fields="id", supportsAllDrives=True).execute()
    return folder.get("id")


def upload_file_to_drive(service, file_path: Path, folder_id: str, mimetype: str):
    """Upload file to Google Drive and return public link."""
    metadata = {"name": file_path.name, "parents": [folder_id]}
    media = MediaFileUpload(str(file_path), mimetype=mimetype)
    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        supportsAllDrives=True,
        fields="id"
    ).execute()
    file_id = uploaded.get("id")
    make_public(service, file_id)
    return f"https://drive.google.com/uc?export=view&id={file_id}"


def write_links_txt(rows, links_path: Path):
    with open(links_path, "w", encoding="utf-8") as f:
        for row in rows:
            sku = row.get("sku", "")
            link = row.get("image_link", "")
            f.write(f"SKU: {sku}\n")
            f.write(f"Link: {link}\n")
            f.write("\n")


def load_links_txt(links_path: Path) -> dict:
    mapping = {}
    if not links_path.exists():
        return mapping
    with open(links_path, "r", encoding="utf-8") as f:
        current_sku = None
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("SKU:"):
                current_sku = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Link:") and current_sku:
                mapping[current_sku] = stripped.split(":", 1)[1].strip()
                current_sku = None
    return mapping


def image_to_base64(img_path: Path) -> str:
    """Convert image to base64 for Ollama."""
    with open(img_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def generate_ollama_description_with_vision(img_path: Path, sku: str, brand: str, finish: str, dimensions: str):
    """Generate product description using Ollama vision model."""
    try:
        metadata_parts = []
        if brand:
            metadata_parts.append(f"Brand: {brand}")
        if finish:
            metadata_parts.append(f"Finish: {finish}")
        if dimensions:
            metadata_parts.append(f"Dimensions: {dimensions}")
        
        metadata_context = "Additional info: " + ", ".join(metadata_parts) if metadata_parts else ""
        
        prompt = ECOMMERCE_PROMPT_TEMPLATE.format(
            sku=sku,
            metadata_context=metadata_context
        )
        
        # Encode image to base64
        img_data = image_to_base64(img_path)
        
        # Send to Ollama with vision
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "images": [img_data],
            "stream": False
        }
        
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        description = result.get("response", "").strip()
        
        return description if description else f"{sku} - Premium product"
    except Exception as exc:
        print(f"     ⚠️  Ollama vision failed: {exc}")
        return f"{sku} - Professional-grade product"


def get_txt_path():
    path = choose_txt_file()
    if path:
        return path
    raw = input("\n📂 Enter path to corrected_metadata.txt (or press Enter for current dir): ").strip().strip('"')
    if raw:
        return raw
    current = Path.cwd() / "corrected_metadata.txt"
    if current.exists():
        return str(current)
    fallback = Path.cwd() / "extracted_text" / "corrected_metadata.txt"
    return str(fallback) if fallback.exists() else ""


def parse_corrected_txt(txt_path):
    """Parse the corrected metadata TXT file into rows."""
    rows = []
    current = {}
    reading_raw = False

    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if not stripped.strip():
                continue
            if stripped.startswith("-") and len(stripped.strip()) >= 10:
                if current:
                    rows.append(current)
                    current = {}
                reading_raw = False
                continue
            if stripped.strip() == "Raw Text Below Image:":
                reading_raw = True
                current["raw_text"] = ""
                continue
            if reading_raw:
                if stripped.startswith("  "):
                    current["raw_text"] += stripped.strip() + " "
                    continue
                reading_raw = False
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                current[key.strip().lower().replace(" ", "_")] = value.strip()

    if current:
        rows.append(current)

    return rows


def main():
    print("=" * 60)
    print("STEP 3: Upload images and create Excel with AI descriptions")
    print("=" * 60)
    
    print(f"\n🔑 Google Drive Folder ID (hardcoded): {GOOGLE_DRIVE_FOLDER_ID}")
    if GOOGLE_DRIVE_FOLDER_ID == "YOUR_GOOGLE_DRIVE_FOLDER_ID_HERE":
        print("❌ ERROR: Please update GOOGLE_DRIVE_FOLDER_ID in this script!")
        return

    txt_path = Path(get_txt_path())
    if not txt_path.exists():
        print("\n❌ Could not locate corrected_metadata.txt.")
        return

    base_dir = txt_path.resolve().parent
    if txt_path.suffix.lower() == ".txt":
        rows = parse_corrected_txt(txt_path)
        df = pd.DataFrame(rows)
    else:
        df = pd.read_csv(str(txt_path), dtype=str).fillna("")

    if "labelled_image_path" not in df.columns:
        labelled_folder = base_dir / "labelled_images"
        if not labelled_folder.exists():
            print("\n❌ labelled_images/ folder not found. Run Step 2 first.")
            return
        df["labelled_image_path"] = df["sku"].apply(lambda sku: str(labelled_folder / f"{sku}.png"))

    print("\n🔐 Authenticating with Google Drive...")
    try:
        drive_service = authenticate_drive(base_dir)
        print("   ✅ Authenticated")
    except Exception as exc:
        print(f"   ❌ Drive auth failed: {exc}")
        return

    upload_root_name = f"Catalog Upload {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    images_folder_name = "images"
    excel_folder_name = "excel"

    print("\n☁️  Creating Google Drive upload folders...")
    upload_root_id = create_drive_folder(drive_service, GOOGLE_DRIVE_FOLDER_ID, upload_root_name)
    images_folder_id = create_drive_folder(drive_service, upload_root_id, images_folder_name)
    excel_folder_id = create_drive_folder(drive_service, upload_root_id, excel_folder_name)
    print(f"   ✅ Upload root folder created: {upload_root_name}")

    print("\n🤖 Generating AI descriptions using Ollama vision...")
    print("   (This may take a moment per image...)")
    descriptions = []
    for idx, (_, row) in enumerate(df.iterrows(), 1):
        sku = row.get("sku", "UNKNOWN")
        img_path = Path(row.get("labelled_image_path", ""))

        if not img_path.exists():
            print(f"   ⚠️  Image missing: {sku}")
            descriptions.append(f"{sku} - Product")
            continue

        print(f"   [{idx}/{len(df)}] {sku}...", end=" ", flush=True)
        desc = generate_ollama_description_with_vision(
            img_path,
            sku,
            row.get("brand", ""),
            row.get("finish", ""),
            row.get("dimensions", "")
        )
        descriptions.append(desc)
        print("✅")
    df["Description"] = descriptions

    print("\n☁️  Uploading labelled images to Google Drive...")
    link_rows = []
    for idx, (_, row) in enumerate(df.iterrows(), 1):
        sku = row.get("sku", "")
        img_path = Path(row.get("labelled_image_path", ""))
        if not img_path.exists():
            print(f"   [{idx}/{len(df)}] ⚠️ {sku} - image missing")
            link_rows.append({"sku": sku, "image_link": ""})
            continue

        try:
            link = upload_file_to_drive(
                drive_service, img_path, images_folder_id, mimetype="image/png"
            )
            link_rows.append({"sku": sku, "image_link": link})
            print(f"   [{idx}/{len(df)}] ✅ {sku}")
        except Exception as exc:
            print(f"   [{idx}/{len(df)}] ❌ {sku}: {exc}")
            link_rows.append({"sku": sku, "image_link": ""})

    links_path = base_dir / "image_links.txt"
    write_links_txt(link_rows, links_path)
    print(f"\n📄 SKU link file created: {links_path}")

    link_map = load_links_txt(links_path)
    df["Image Link"] = df["sku"].map(link_map).fillna("")

    # Check for Excel template
    print("\n📋 Excel template option:")
    template_path = get_template_path_from_config(base_dir)
    
    if template_path:
        print(f"   Found template from Step 1: {Path(template_path).name}")
        use_template = input("   Use this template? (y/n): ").strip().lower() == 'y'
    else:
        use_template = input("   Use custom Excel template? (y/n): ").strip().lower() == 'y'
    
    if use_template:
        if not template_path:
            template_path = choose_excel_template()
        
        if template_path and Path(template_path).exists():
            try:
                template_df = pd.read_excel(template_path)
                for col in template_df.columns:
                    if col in df.columns:
                        template_df[col] = df[col]
                final_df = template_df
                print(f"   ✅ Template loaded: {Path(template_path).name}")
            except Exception as exc:
                print(f"   ⚠️  Template loading failed: {exc}, using default format")
                final_df = df[[c for c in ["sku", "brand", "finish", "dimensions", "Description", "Image Link"] if c in df.columns]]
        else:
            final_df = df[[c for c in ["sku", "brand", "finish", "dimensions", "Description", "Image Link"] if c in df.columns]]
    else:
        columns_order = ["sku", "brand", "finish", "dimensions", "Description", "Image Link"]
        available_cols = [c for c in columns_order if c in df.columns]
        final_df = df[available_cols]

    # Rename columns for display
    final_df = final_df.rename(columns={
        "sku": "SKU",
        "brand": "Brand",
        "finish": "Finish",
        "dimensions": "Dimensions"
    })

    excel_path = base_dir / "product_catalog.xlsx"
    final_df.to_excel(str(excel_path), index=False)
    print(f"\n📄 Excel created: {excel_path}")

    try:
        print("☁️  Uploading Excel to Google Drive...")
        excel_link = upload_file_to_drive(
            drive_service,
            excel_path,
            excel_folder_id,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        print(f"✅ Uploaded Excel: {excel_link}")
    except Exception as exc:
        print(f"⚠️  Excel upload failed: {exc}")

    try:
        print("☁️  Uploading link manifest to Google Drive...")
        links_drive_link = upload_file_to_drive(
            drive_service,
            links_path,
            excel_folder_id,
            mimetype="text/plain"
        )
        print(f"✅ Uploaded link manifest: {links_drive_link}")
    except Exception as exc:
        print(f"⚠️  Link manifest upload failed: {exc}")

    print("\n✅ Step 3 complete!")
    print(f"   📊 Excel: {excel_path}")
    print(f"   📄 Link manifest: {links_path}")
    print(f"   📁 Drive root folder: {upload_root_name}")
    print(f"   📂 Images folder ID: {images_folder_id}")
    print(f"   📂 Excel folder ID: {excel_folder_id}")


if __name__ == "__main__":
    main()
