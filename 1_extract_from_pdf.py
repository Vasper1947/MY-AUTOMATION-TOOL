#!/usr/bin/env python3
"""
Step 1: Extract images and metadata from PDF(s).
Saves extracted images named by SKU and creates extracted_data.csv.
Supports multiple PDFs and highly interactive field confirmation.
"""

import io
import os
import re
import csv
import shutil
import json
import socket
import fitz
from PIL import Image, ImageEnhance
from pathlib import Path

try:
    import pytesseract
    pytesseract_cmd = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
    if pytesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = pytesseract_cmd
        OCR_AVAILABLE = True
    else:
        pytesseract = None
        OCR_AVAILABLE = False
except ImportError:
    pytesseract = None
    OCR_AVAILABLE = False

SKU_PATTERN = r"\b(\d{4,7})\b"
DIMENSION_PATTERN = r"(\d+\s*[xX]\s*\d+\s*(?:MM|mm|CM|cm|IN|in|INCH|inch|FT|ft))"
PAGE_HEADER_TOLERANCE = 100  # pixels from top to search for page title/brand/dimensions
UNDER_IMAGE_TOLERANCE = 100
OLLAMA_LOCAL_URL = "http://localhost:11434"
OLLAMA_NETWORK_URL = None  # Will be auto-detected


def get_local_ip():
    """Get local network IP address for Ollama phone access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def detect_ollama_url(ollama_port=11434):
    """Detect if Ollama is running locally or on network. Return accessible URL."""
    global OLLAMA_NETWORK_URL
    
    import requests
    
    # Try localhost first (fastest)
    try:
        resp = requests.get(f"{OLLAMA_LOCAL_URL}/api/tags", timeout=2)
        if resp.status_code == 200:
            return OLLAMA_LOCAL_URL
    except Exception:
        pass
    
    # Try local network IP
    try:
        local_ip = get_local_ip()
        network_url = f"http://{local_ip}:{ollama_port}"
        resp = requests.get(f"{network_url}/api/tags", timeout=2)
        if resp.status_code == 200:
            OLLAMA_NETWORK_URL = network_url
            return network_url
    except Exception:
        pass
    
    return None


def enhance_image(image_path, output_path):
    """Enhance image: auto-crop, upscale, boost contrast/saturation."""
    img = Image.open(image_path).convert("RGB")
    original_size = img.size
    
    # Auto-crop whitespace (tolerance: 240)
    bbox = img.getbbox()
    if bbox and bbox != (0, 0, img.width, img.height):
        img = img.crop(bbox)
    
    # Upscale 4x using high-quality resampling
    new_size = (img.width * 4, img.height * 4)
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.2)
    
    # Enhance color saturation
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.15)
    
    img.save(output_path, quality=95)
    return new_size


def generate_image_variants(image_path, output_dir, sku):
    """Generate image variants (perspective, color, rotation)."""
    img = Image.open(image_path).convert("RGB")
    variants = {}
    
    # Variant 1: Rotated slightly left
    try:
        rotated = img.rotate(3, expand=False, resample=Image.Resampling.BICUBIC)
        variant_path = output_dir / f"variant_rotated_left.png"
        rotated.save(variant_path, quality=95)
        variants["rotated_left"] = str(variant_path)
    except Exception:
        pass
    
    # Variant 2: Rotated slightly right
    try:
        rotated = img.rotate(-3, expand=False, resample=Image.Resampling.BICUBIC)
        variant_path = output_dir / f"variant_rotated_right.png"
        rotated.save(variant_path, quality=95)
        variants["rotated_right"] = str(variant_path)
    except Exception:
        pass
    
    # Variant 3: Color-shifted (warmer tone)
    try:
        enhancer = ImageEnhance.Color(img)
        warm = enhancer.enhance(1.3)
        variant_path = output_dir / f"variant_warm.png"
        warm.save(variant_path, quality=95)
        variants["warm_tone"] = str(variant_path)
    except Exception:
        pass
    
    # Variant 4: Brightness adjusted
    try:
        enhancer = ImageEnhance.Brightness(img)
        bright = enhancer.enhance(1.1)
        variant_path = output_dir / f"variant_bright.png"
        bright.save(variant_path, quality=95)
        variants["bright"] = str(variant_path)
    except Exception:
        pass
    
    return variants


def choose_pdf_file():
    # try:
    #     import tkinter as tk
    #     from tkinter import filedialog
    #     root = tk.Tk()
    #     root.withdraw()
    #     path = filedialog.askopenfilename(title="Select catalog PDF", filetypes=[("PDF files", "*.pdf")])
    #     root.destroy()
    #     return path
    # except Exception:
    #     return ""
    return ""


def ask_for_path():
    candidate = choose_pdf_file()
    if candidate:
        return candidate
    raw = input("\n📁 Enter PDF or folder path: ").strip().strip('"')
    return raw


def get_image_rectangles(page):
    rects = []
    for img in page.get_images(full=True):
        xref = img[0]
        for rect in page.get_image_rects(xref):
            rects.append((xref, rect))
    return rects


def get_text_spans(page):
    spans = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text:
                    spans.append((text, fitz.Rect(span.get("bbox", []))))
    return spans


def render_page_image(page, dpi=200):
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
    mode = "RGB" if pix.n == 3 else "RGBA"
    return Image.frombytes(mode, [pix.width, pix.height], pix.samples)


def scale_rect_to_image(rect, page, image_size):
    page_w, page_h = page.rect.width, page.rect.height
    img_w, img_h = image_size
    x0 = int(rect.x0 / page_w * img_w)
    y0 = int(rect.y0 / page_h * img_h)
    x1 = int(rect.x1 / page_w * img_w)
    y1 = int(rect.y1 / page_h * img_h)
    return x0, y0, x1, y1


def ocr_text_below_image(page, page_image, img_rect, margin=50, height=220):
    if not OCR_AVAILABLE:
        return ""
    x0, y0, x1, y1 = scale_rect_to_image(img_rect, page, page_image.size)
    x0 = max(0, x0 - margin)
    x1 = min(page_image.width, x1 + margin)
    y1 = min(page_image.height, y1 + height)
    region = page_image.crop((x0, y0, x1, y1))
    try:
        return pytesseract.image_to_string(region, lang="eng")
    except Exception:
        return ""


def find_text_below_image(img_rect, spans, tolerance):
    below = []
    for text, bbox in spans:
        if bbox.y0 >= img_rect.y1 and bbox.y0 - img_rect.y1 <= tolerance:
            if bbox.x1 >= img_rect.x0 and bbox.x0 <= img_rect.x1:
                below.append((bbox.y0, text))
    below.sort(key=lambda x: x[0])
    return [text for _, text in below]


def extract_page_header_metadata(page, page_top_region=100):
    """Extract product title, brand, and dimensions from top of page."""
    spans = get_text_spans(page)
    
    page_header = {
        "category": "",
        "brand": "",
        "page_dimensions": ""
    }
    
    header_text_lines = []
    for text, bbox in spans:
        if bbox.y0 <= page_top_region:
            header_text_lines.append(text.strip())
    
    header_text = " ".join(header_text_lines)
    
    # Look for dimensions pattern (e.g., 250X400MM)
    dim_match = re.search(DIMENSION_PATTERN, header_text, re.I)
    if dim_match:
        page_header["page_dimensions"] = dim_match.group(1).strip()
        
    # Everything before dimensions is likely category and brand
    if dim_match:
        pre_dim_text = header_text[:dim_match.start()].strip()
    else:
        pre_dim_text = header_text
    
    lines = [l.strip() for l in pre_dim_text.split("\n") if l.strip()]
    
    if len(lines) >= 2:
        page_header["brand"] = lines[-1]  # Last line is usually brand
        page_header["category"] = " ".join(lines[:-1])  # Everything else is category
    elif len(lines) == 1:
        page_header["category"] = lines[0]
    
    return page_header


def extract_metadata(lines):
    """Extract metadata from lines below image for review display."""
    content = " ".join(lines)
    sku_match = re.search(SKU_PATTERN, content, re.I)
    dim_match = re.search(DIMENSION_PATTERN, content, re.I)
    return {
        "sku": sku_match.group(1).strip() if sku_match else "",
        "brand": "",
        "finish": "",
        "dimensions": dim_match.group(1).strip() if dim_match else "",
        "original_desc": content.strip()
    }


def extract_skus_from_text_lines(lines):
    """Find numeric SKU candidates in the extracted text lines.

    SKU values are not explicitly labeled in the catalog; this helper
    looks for likely numeric identifiers around each image and excludes
    page dimensions.
    """
    skus = []
    for line in lines:
        # Exclude obvious dimension strings from SKU matching.
        filtered_line = re.sub(DIMENSION_PATTERN, "", line, flags=re.I)
        for match in re.finditer(SKU_PATTERN, filtered_line):
            sku = match.group(1).strip()
            if sku and sku not in skus:
                skus.append(sku)

    if len(skus) > 1:
        # Prefer longer candidates first as they are more likely to be product SKUs.
        skus.sort(key=lambda value: (-len(value), skus.index(value)))

    return skus


def get_ollama_description(image_path, model="llava", ollama_url=None):
    """Generate product description using Ollama's image analysis."""
    if not ollama_url:
        ollama_url = OLLAMA_LOCAL_URL
    
    try:
        import requests
        import base64
        
        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Call Ollama API
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": "Describe this product image in detail. Focus on: color, texture, patterns, material appearance, and style. Be concise but descriptive (2-3 sentences).",
                "images": [image_data],
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            return ""
    except Exception as e:
        return f"(AI description unavailable: {str(e)})"


def build_metadata_text_block(row, raw_lines):
    """Format one product entry as editable text."""
    lines = ["-" * 70]
    lines.append(f"Page: {row['page']}")
    lines.append(f"Image Index: {row['image_index']}")
    lines.append(f"SKU: {row['sku']}")
    lines.append(f"SKU Folder: {row.get('sku_folder', 'N/A')}")
    lines.append(f"Original Image: {row.get('original_image', 'N/A')}")
    lines.append(f"Enhanced Image: {row.get('enhanced_image', 'N/A')}")
    variants = json.loads(row.get('variant_images', '{}')) if isinstance(row.get('variant_images'), str) else row.get('variant_images', {})
    if variants:
        lines.append(f"Variants: {', '.join(variants.keys())}")
    lines.append(f"Image Dimensions: {row.get('image_width', 'N/A')}x{row.get('image_height', 'N/A')} px ({row.get('orientation', 'N/A')})")
    lines.append(f"Category: {row.get('category', '')}")
    lines.append(f"Brand: {row.get('brand', '')}")
    lines.append(f"Product Dimensions: {row.get('dimensions', '')}")
    lines.append(f"AI Description: {row.get('ai_description', '')}")
    lines.append("Raw Text Below Image:")
    if raw_lines:
        for raw_line in raw_lines:
            lines.append(f"  {raw_line}")
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def choose_xlsx_template():
    """Ask user to select an Excel template file for final output."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="Select Excel template for final spreadsheet (optional - press Cancel to skip)",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        root.destroy()
        return path if path else None
    except Exception:
        return None


def get_page_text_organized(doc, page_number, images_info):
    """Extract all text from page in organized format for review."""
    page = doc[page_number]
    page_text = []
    page_text.append(f"\n{'='*70}")
    page_text.append(f"PAGE {page_number + 1}")
    page_text.append(f"{'='*70}\n")
    
    if not images_info:
        page_text.append("(No images on this page)\n")
        return "\n".join(page_text)
    
    spans = get_text_spans(page)
    page_image = render_page_image(page) if OCR_AVAILABLE else None
    
    for img_idx, (xref, img_rect) in enumerate(images_info, start=1):
        page_text.append(f"\nImage {img_idx}:")
        page_text.append("-" * 50)
        
        lines = find_text_below_image(img_rect, spans, UNDER_IMAGE_TOLERANCE)
        if not lines and OCR_AVAILABLE:
            ocr_text = ocr_text_below_image(page, page_image, img_rect)
            lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        
        if lines:
            raw_text = " ".join(lines)
            page_text.append(f"Raw text below image:\n{raw_text}\n")
            
            meta = extract_metadata(lines)
            page_text.append(f"Extracted metadata:")
            page_text.append(f"  SKU: {meta.get('sku', '(not found)')}")
            page_text.append(f"  Brand: {meta.get('brand', '(not found)')}")
            page_text.append(f"  Finish: {meta.get('finish', '(not found)')}")
            page_text.append(f"  Dimensions: {meta.get('dimensions', '(not found)')}")
            page_text.append(f"  Description: {meta.get('original_desc', '(not found)')}")
        else:
            page_text.append("(No text found below image)\n")
    
    return "\n".join(page_text)


def main():
    print("=" * 60)
    print("STEP 1: Extract images and metadata from PDF(s)")
    print("=" * 60)

    base_workspace = Path(ask_for_path())
    if not base_workspace.exists():
        base_workspace = Path.cwd()
    if base_workspace.is_file():
        base_workspace = base_workspace.parent
    
    print(f"\n📁 Using workspace: {base_workspace}")
    if not OCR_AVAILABLE:
        print("⚠️  OCR disabled: tesseract is not installed or not found in PATH.")
        print("   Install Tesseract OCR and add it to PATH, or set TESSERACT_CMD to the tesseract.exe path.")
        print("   The script will continue, but OCR-based text extraction will be skipped.")
    
    extracted_base = base_workspace / "extracted_images"
    extracted_base.mkdir(parents=True, exist_ok=True)
    
    extracted_text_base = base_workspace / "extracted_text"
    extracted_text_base.mkdir(parents=True, exist_ok=True)

    pdf_files = list(base_workspace.glob("*.pdf"))
    if not pdf_files:
        print("❌ No PDF files found in workspace.")
        return

    print(f"\n📄 Found {len(pdf_files)} PDF file(s):")
    for i, pdf in enumerate(pdf_files, 1):
        print(f"  {i}. {pdf.name}")

    process_all = input("\nProcess all PDFs? (y/n): ").strip().lower() == 'y'
    if not process_all:
        try:
            idx = int(input("Enter PDF number to process (or 0 to exit): ")) - 1
            if idx < 0 or idx >= len(pdf_files):
                return
            pdf_files = [pdf_files[idx]]
        except ValueError:
            return

    all_rows = []

    for pdf_path in pdf_files:
        print(f"\n🔄 Processing: {pdf_path.name}")
        doc = fitz.open(str(pdf_path))
        sku_counter = {}
        text_output = [f"EXTRACTED TEXT METADATA FROM: {pdf_path.name}",
                       "Generated for review and verification",
                       "" + "=" * 70]

        for page_number in range(len(doc)):
            page = doc[page_number]
            print(f"  Page {page_number + 1}/{len(doc)}...", end=" ")
            images = get_image_rectangles(page)
            spans = get_text_spans(page)

            if not images:
                print("(no images)")
                continue

            # Extract page-level metadata
            page_header = extract_page_header_metadata(page, PAGE_HEADER_TOLERANCE)
            print(f"[{page_header.get('category', 'Unknown')}]")

            page_text = get_page_text_organized(doc, page_number, images)
            text_output.append(page_text)

            page_image = render_page_image(page) if OCR_AVAILABLE else None

            for image_index, (xref, img_rect) in enumerate(images, start=1):
                image_info = doc.extract_image(xref)
                image_bytes = image_info.get("image")

                lines = find_text_below_image(img_rect, spans, UNDER_IMAGE_TOLERANCE)
                if not lines and OCR_AVAILABLE:
                    ocr_text = ocr_text_below_image(page, page_image, img_rect)
                    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]

                # Extract SKU from lines below image
                skus = extract_skus_from_text_lines(lines)
                sku = skus[0] if skus else ""

                if not sku:
                    sku = f"AUTO_{page_number + 1}_{image_index}"

                if sku in sku_counter:
                    sku_counter[sku] += 1
                    unique_sku = f"{sku}_v{sku_counter[sku]}"
                else:
                    sku_counter[sku] = 1
                    unique_sku = sku

                # Create per-SKU folder structure
                sku_folder = extracted_base / unique_sku
                sku_folder.mkdir(parents=True, exist_ok=True)
                
                # Save original image
                original_path = sku_folder / "original.png"
                pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                pil_image.save(str(original_path))
                
                # Enhance image
                enhanced_path = sku_folder / "enhanced.png"
                try:
                    enhance_image(str(original_path), str(enhanced_path))
                except Exception as e:
                    print(f"\n    ⚠️ Enhancement failed: {e}")
                    shutil.copy(str(original_path), str(enhanced_path))
                
                # Generate variants
                variants = {}
                try:
                    variants = generate_image_variants(str(original_path), sku_folder, unique_sku)
                except Exception as e:
                    print(f"\n    ⚠️ Variant generation failed: {e}")
                
                print(f"\n    ✅ {unique_sku} ({pil_image.width}x{pil_image.height})", end=" ")

                # Extract per-image dimensions if available
                image_dimensions = ""
                for line in lines:
                    dim_match = re.search(DIMENSION_PATTERN, line, re.I)
                    if dim_match:
                        image_dimensions = dim_match.group(1).strip()
                        break

                # Use page-level dimensions as fallback
                final_dimensions = image_dimensions or page_header.get("page_dimensions", "")

                row = {
                    "page": page_number + 1,
                    "image_index": image_index,
                    "sku": unique_sku,
                    "sku_folder": str(sku_folder),
                    "original_image": str(original_path),
                    "enhanced_image": str(enhanced_path),
                    "variant_images": json.dumps(variants),
                    "category": page_header.get("category", ""),
                    "brand": page_header.get("brand", ""),
                    "dimensions": final_dimensions,
                    "image_width": pil_image.width,
                    "image_height": pil_image.height,
                    "orientation": "landscape" if pil_image.width > pil_image.height else "portrait",
                    "ai_description": ""
                }
                
                # Save per-SKU metadata.json
                metadata = {
                    "sku": unique_sku,
                    "page": page_number + 1,
                    "category": row.get("category", ""),
                    "brand": row.get("brand", ""),
                    "dimensions": row.get("dimensions", ""),
                    "image_width": row.get("image_width"),
                    "image_height": row.get("image_height"),
                    "orientation": row.get("orientation"),
                    "extracted_text": " ".join(lines) if lines else ""
                }
                
                metadata_json_path = sku_folder / "metadata.json"
                with open(metadata_json_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
                
                all_rows.append(row)
                text_output.append(build_metadata_text_block(row, lines))

            print()

        doc.close()
        
        metadata_file_path = extracted_text_base / f"{pdf_path.stem}_metadata.txt"
        with open(metadata_file_path, "w", encoding="utf-8") as txtfile:
            txtfile.write("\n\n".join(text_output))
        print(f"  📄 Metadata text saved: {metadata_file_path.name}")

    print(f"\n✅ Extraction complete.")
    print(f"   Folder structure: extracted_images/SKU_001/, SKU_002/, etc.")
    print(f"   Each folder contains: original.png, enhanced.png, variants_*.png, metadata.json")
    print(f"   Metadata TXT folder: {extracted_text_base}")
    print(f"   Total products extracted: {len(all_rows)}")
    
    # Detect Ollama
    print(f"\n🤖 DETECTING OLLAMA SERVICE...")
    ollama_url = detect_ollama_url()
    
    if ollama_url:
        print(f"   ✅ Ollama found at: {ollama_url}")
        if OLLAMA_NETWORK_URL:
            print(f"   📱 Phone access: http://{get_local_ip()}:11434")
        generate_ai = input("Generate AI descriptions for products? (y/n): ").strip().lower() == 'y'
    else:
        print(f"   ⚠️ Ollama not detected. Install Ollama and run 'ollama serve'")
        print(f"   For phone access, set OLLAMA_HOST=0.0.0.0:11434 before running ollama serve")
        generate_ai = False
    
    if generate_ai:
        print("Starting AI description generation...")
        for i, row in enumerate(all_rows, 1):
            try:
                # Use enhanced image for better AI analysis
                enhanced_img_path = row.get("enhanced_image", row.get("original_image"))
                desc = get_ollama_description(enhanced_img_path, model="llava", ollama_url=ollama_url)
                row["ai_description"] = desc
                
                # Update metadata.json with description
                metadata_json_path = Path(row["sku_folder"]) / "metadata.json"
                if metadata_json_path.exists():
                    with open(metadata_json_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    metadata["ai_description"] = desc
                    with open(metadata_json_path, "w", encoding="utf-8") as f:
                        json.dump(metadata, f, indent=2)
                
                print(f"  [{i}/{len(all_rows)}] {row['sku']}: ✅")
            except Exception as e:
                print(f"  [{i}/{len(all_rows)}] {row['sku']}: ⚠️ {str(e)}")
    
    # Save extracted data to CSV
    csv_path = extracted_text_base / "extracted_data.csv"
    if all_rows:
        csv_headers = [
            "page", "image_index", "sku", "sku_folder", "original_image", "enhanced_image", "variant_images",
            "category", "brand", "dimensions", "image_width", "image_height", "orientation", "ai_description"
        ]
        with open(csv_path, "w", encoding="utf-8", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
            writer.writeheader()
            for row in all_rows:
                filtered_row = {k: row.get(k, "") for k in csv_headers}
                writer.writerow(filtered_row)
        print(f"\n📊 CSV saved: {csv_path.name}")
    
    print(f"\n📋 IMPORTANT - Select Excel Template")
    print(f"   The template defines columns for your final spreadsheet.")
    template_path = choose_xlsx_template()
    
    if template_path:
        config_path = base_workspace / "template_config.txt"
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(f"EXCEL_TEMPLATE_PATH={template_path}\n")
        print(f"   Template saved: {template_path}")
    else:
        print(f"   No template selected (Step 3 will create default spreadsheet)")
    
    print(f"\n📌 FOLDER STRUCTURE:")
    print(f"   extracted_images/")
    print(f"   ├── SKU_001/")
    print(f"   │   ├── original.png (from PDF)")
    print(f"   │   ├── enhanced.png (upscaled 4x, enhanced)")
    print(f"   │   ├── variant_*.png (rotations, color variants)")
    print(f"   │   └── metadata.json (all product data)")
    print(f"   ├── SKU_002/")
    print(f"   │   └── ... (same structure)")
    print(f"\n📌 Next steps:")
    print(f"   1. Review the CSV: {csv_path.name}")
    print(f"   2. Inspect extracted images in folder structure: {extracted_base}")
    print(f"   3. Run 2_review_and_label.py to manually verify")
    print(f"   4. Run 3_upload_and_excel.py to finalize and fill spreadsheet")


if __name__ == "__main__":
    main()
