import os
import re
import traceback
from shutil import move
from pathlib import Path
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import requests

# Configuration
poppler_path = r'Release-24.08.0-0/poppler-24.08.0/Library/bin'
tesseract_cmd_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_path

# ------------------ OCR Helpers ------------------

def fuzzy_match(a: str, b: str, threshold: float = 0.9) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= threshold

def find_phrase_on_page(page, phrase, threshold=0.9):
    try:
        data = pytesseract.image_to_data(page, output_type=pytesseract.Output.DICT)
        words = [w.lower() for w in data['text']]
        tgt_words = phrase.lower().split()
        n = len(tgt_words)

        for i in range(len(words) - n + 1):
            candidate = " ".join(words[i:i + n])
            if fuzzy_match(candidate, phrase.lower(), threshold):
                tops = data['top'][i:i + n]
                heights = data['height'][i:i + n]
                return min(tops), max(t + h for t, h in zip(tops, heights))
    except Exception as e:
        print(f"❌ OCR error on page finding '{phrase}': {e}")
        traceback.print_exc()
    return None

def find_all_segments_on_pages(pages, start_phrase, end_phrase, threshold=0.9):
    segments = []

    for pi, page in enumerate(pages):
        try:
            # 🧠 OCR the page to extract raw text first
            page_text = pytesseract.image_to_string(page).lower().strip()
        except Exception as e:
            print(f"❌ OCR text extraction failed on page {pi}: {e}")
            continue

        # Step 1: Does page contain "on the dirt"?
        if "on the dirt" not in page_text:
            continue  # Skip this page

        # Step 2: Find start phrase on this page
        start_res = find_phrase_on_page(page, start_phrase, threshold)
        if not start_res:
            continue

        # Step 3: Find end phrase on this page, after start
        end_res = find_phrase_on_page(page, end_phrase, threshold)
        if not end_res:
            continue

        start_index = start_res[0]
        end_index = end_res[1]

        if end_index > start_index:
            segments.append((pi, start_index, pi, end_index))

    return segments

# ------------------ Image Cropping ------------------

def crop_segment(pages, basename, out_folder, seg_index,
                 start_page, start_y, end_page, end_y,
                 padding=20):
    try:
        crops = []
        W = pages[0].size[0]
        for idx in range(start_page, end_page + 1):
            page = pages[idx]
            _, H = page.size
            if idx == start_page == end_page:
                y0, y1 = max(0, start_y - padding), min(H, end_y + padding)
            elif idx == start_page:
                y0, y1 = max(0, start_y - padding), H
            elif idx == end_page:
                y0, y1 = 0, min(H, end_y + padding)
            else:
                y0, y1 = 0, H
            crops.append(page.crop((0, y0, W, y1)))

        total_h = sum(c.size[1] for c in crops)
        stitched = Image.new("RGB", (W, total_h), "white")
        off = 0
        for c in crops:
            stitched.paste(c, (0, off))
            off += c.size[1]

        out_name = f"{basename}_race_{seg_index}.png"
        out_path = os.path.join(out_folder, out_name)
        stitched.save(out_path, dpi=(300, 300))
        print(f"✅ Saved: {out_name}")
    except Exception as e:
        print(f"❌ Error saving cropped image for {basename} segment {seg_index}: {e}")
        traceback.print_exc()

def process_multiple_segments(pdf_path, out_folder, segment_specs):
    os.makedirs(out_folder, exist_ok=True)
    basename = Path(pdf_path).stem

    try:
        pages = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)
    except Exception as e:
        print(f"❌ Failed to convert {pdf_path} to images: {e}")
        traceback.print_exc()
        return

    for spec in segment_specs:
        try:
            segments = find_all_segments_on_pages(
                pages, spec['start'], spec['end'],
                threshold=spec.get('threshold', 0.9)
            )
        except Exception as e:
            print(f"❌ Error finding segments in {basename}: {e}")
            traceback.print_exc()
            continue

        if not segments:
            print(f"⚠️ No segments found for {basename} with phrases "
                  f"'{spec['start']}' → '{spec['end']}'")
            continue

        for idx, (si, sy, ei, ey) in enumerate(segments, start=1):
            crop_segment(
                pages, basename, out_folder, idx,
                si, sy, ei, ey,
                padding=spec.get('padding', 20)
            )

# ------------------ Download & CSV ------------------

def download_pdf(url, save_path):
    try:
        headers = {
            'user-agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/91.0.4472.114 Safari/537.36'
            )
        }
        r = requests.get(url, stream=True, headers=headers, timeout=30)
        if r.headers.get('Content-Type') == 'application/pdf':
            with open(save_path, "wb") as f:
                f.write(r.content)
            print(f"✅ PDF downloaded: {save_path}")
            return True
        else:
            print(f"❌ Not a PDF at URL: {url}")
    except Exception as e:
        print(f"❌ Error downloading {url}: {e}")
        traceback.print_exc()
    return False

def process_csv_and_download(csv_file, download_dir, output_dir,
                             segment_specs, max_workers=None):
    os.makedirs(download_dir, exist_ok=True)
    df = pd.read_csv(csv_file)

    def _process_row(index, row):
        try:
            track = row['track_name'].replace(" ", "_")
            date = row['date']
            base_name = f"{track}_{date}"
            pdf_url = row['pdf_url']
            pdf_path = os.path.join(download_dir, f"{base_name}.pdf")

            if download_pdf(pdf_url, pdf_path):
                process_multiple_segments(pdf_path, output_dir, segment_specs)
        except Exception as e:
            print(f"❌ Error processing row {index} ({row.get('pdf_url')}): {e}")
            traceback.print_exc()

    # default threads = cpu_count or fallback to 4
    workers = max_workers or (os.cpu_count() or 4)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_process_row, idx, row): idx
            for idx, row in df.iterrows()
        }
        for future in as_completed(futures):
            # any exception in _process_row is already caught, so this is just to drain
            pass

def group_images_by_segment(src_folder):
    try:
        for fname in os.listdir(src_folder):
            if not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
            match = re.search(r'_race_(\d+)', fname)
            if match:
                race_num = match.group(1)
                race_folder = os.path.join(src_folder, f"race_{race_num}")
                os.makedirs(race_folder, exist_ok=True)
                move(
                    os.path.join(src_folder, fname),
                    os.path.join(race_folder, fname)
                )
                print(f"Moved {fname} → race_{race_num}/")
    except Exception as e:
        print(f"❌ Error grouping images in {src_folder}: {e}")
        traceback.print_exc()

# ------------------ Run ------------------

if __name__ == "__main__":
    segment_specs = [
        {
            'start': 'Last Raced',
            'end': 'Fractional Times',
            'padding': 30,
            'threshold': 0.85
        }
    ]

    try:
        process_csv_and_download(
            csv_file="pdf_data.csv",
            download_dir="pdfs",
            output_dir="cropped_images",
            segment_specs=segment_specs,
            max_workers=5  # or set an int
        )
    except Exception as e:
        print(f"❌ Unexpected error in download/process pipeline: {e}")
        traceback.print_exc()

    try:
        group_images_by_segment("cropped_images")
    except Exception as e:
        print(f"❌ Unexpected error grouping images: {e}")
        traceback.print_exc()
