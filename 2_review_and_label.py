#!/usr/bin/env python3
"""
Step 2: Review each image, confirm/correct SKU, then label image with SKU.
"""

import os
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def label_image_with_sku(img_path, sku, output_path):
    """Draw SKU at bottom-right of image with better sizing."""
    img = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    font_size = max(24, img.width // 20)
    try:
        font = ImageFont.truetype("arial.ttf", size=font_size)
    except Exception:
        font = ImageFont.load_default()
    text = sku.strip() or "UNKNOWN"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    padding = int(font_size * 0.35)
    x = img.width - text_w - padding * 2
    y = img.height - text_h - padding * 2
    draw.rectangle([x, y, x + text_w + padding * 2, y + text_h + padding * 2], fill="white")
    draw.text((x + padding, y + padding), text, fill="black", font=font)
    img.save(output_path)

def open_image(path):
    """Open image with default OS viewer."""
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])


def get_user_input(prompt, current_value="", required=False):
    """Get user input with option to keep current or enter new."""
    display = f" [{current_value}]" if current_value else ""
    response = input(f"{prompt}{display}: ").strip()
    
    if response:
        return response
    elif current_value:
        return current_value
    elif required:
        return get_user_input(f"{prompt} (REQUIRED)", current_value, required=True)
    else:
        return ""


def parse_metadata_txt(txt_path):
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


def format_metadata_txt(rows, txt_path):
    with open(txt_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write("-" * 70 + "\n")
            f.write(f"Page: {row.get('page', '')}\n")
            f.write(f"Image Index: {row.get('image_index', '')}\n")
            f.write(f"Image File: {row.get('image_file', '')}\n")
            f.write(f"Image Path: {row.get('image_path', '')}\n")
            f.write(f"SKU: {row.get('sku', '')}\n")
            f.write(f"Brand: {row.get('brand', '')}\n")
            f.write(f"Finish: {row.get('finish', '')}\n")
            f.write(f"Dimensions: {row.get('dimensions', '')}\n")
            f.write(f"Description: {row.get('original_desc', '')}\n")
            f.write(f"Labelled Image Path: {row.get('labelled_image_path', '')}\n")
            f.write("Raw Text Below Image:\n")
            raw_text = row.get("raw_text", "").strip()
            if raw_text:
                for fragment in raw_text.split("  "):
                    if fragment.strip():
                        f.write(f"  {fragment.strip()}\n")
            else:
                f.write("  (none)\n")
            f.write("\n")


def main():
    print("=" * 60)
    print("STEP 2: Review and label images (highly interactive)")
    print("=" * 60)

    txt_path = input("\nEnter path to metadata TXT file (or press Enter for extracted_text folder): ").strip().strip('"')
    if not txt_path:
        extracted_text_dir = Path.cwd() / "extracted_text"
        if extracted_text_dir.exists():
            txt_candidates = list(extracted_text_dir.glob("*_metadata.txt"))
            if txt_candidates:
                txt_path = str(txt_candidates[0])
            else:
                print("\n❌ No metadata TXT files found in extracted_text folder.")
                return
        else:
            print("\n❌ extracted_text folder not found. Run Step 1 first.")
            return

    txt_file = Path(txt_path)
    if not txt_file.exists():
        print(f"\n❌ File not found: {txt_path}")
        return

    base_dir = txt_file.resolve().parent
    labelled_dir = base_dir / "labelled_images"
    labelled_dir.mkdir(parents=True, exist_ok=True)

    rows = parse_metadata_txt(txt_file)
    print(f"\nFound {len(rows)} items to review.")

    updated_rows = []
    for index, row in enumerate(rows, start=1):
        print("\n" + "=" * 60)
        print(f"ITEM {index}/{len(rows)}")
        print("=" * 60)
        
        image_path = Path(row.get("image_path", ""))
        if not image_path.exists():
            print(f"Missing image: {image_path}")
            skip = input("Skip this item? (y/n): ").strip().lower()
            if skip == 'y':
                continue
        else:
            print(f"Raw image: {image_path.name}")
            print("\nOpening image for review...")
            open_image(str(image_path))

        print("\nMETADATA REVIEW (leave blank to keep existing value):")
        print("-" * 60)
        
        row["sku"] = get_user_input("SKU", row.get("sku", ""), required=True)
        row["brand"] = get_user_input("Brand", row.get("brand", ""))
        row["finish"] = get_user_input("Finish", row.get("finish", ""))
        row["dimensions"] = get_user_input("Dimensions", row.get("dimensions", ""))
        row["original_desc"] = get_user_input("Description", row.get("original_desc", ""))

        output_name = f"{row['sku']}.png"
        output_path = labelled_dir / output_name
        if output_path.exists():
            output_path = labelled_dir / f"{row['sku']}_{index}.png"

        label_image_with_sku(str(image_path), row["sku"], str(output_path))
        row["labelled_image_path"] = str(output_path)
        print(f"\nLabelled image saved: {output_path.name}")

        updated_rows.append(row)

        if index < len(rows):
            cont = input("\nContinue to next image? (Enter=yes, n=no): ").strip().lower()
            if cont == "n":
                break

    corrected_txt_path = base_dir / "corrected_metadata.txt"
    format_metadata_txt(updated_rows, corrected_txt_path)

    print("\nReview complete.")
    print(f"   Corrected TXT: {corrected_txt_path}")
    print(f"   Labelled images: {labelled_dir}")
    print(f"   Items processed: {len(updated_rows)}")
    print("\nNext: run 3_upload_and_excel.py")


if __name__ == "__main__":
    main()