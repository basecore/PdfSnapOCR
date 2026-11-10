# -*- coding: utf-8 -*-
"""Core functions for PdfSnapOCR: capture, PDF creation and OCR."""

import os, sys, subprocess, importlib, json, time
from pathlib import Path
from datetime import datetime

REQUIRED = ["mss", "pillow", "pymupdf", "keyboard", "ocrmypdf"]
CONFIG_FILE = Path(__file__).with_name("pdfsnapocr_config.json")

DEFAULTS = {
    "output_dir": str(Path.home() / "Documents" / "PdfSnapOCR"),
    "page_mode": "single", "turn_key": "pagedown",
    "delay_after_turn": 1.0, "delay_before_capture": 0.4,
    "max_pages": 200, "auto_stop": True, "change_threshold": 0.985,
    "ocr_enabled": True, "ocr_language": "deu+eng",
}

def ensure_packages():
    missing = []
    for name in REQUIRED:
        try: importlib.import_module(name)
        except ImportError: missing.append(name)
    if missing:
        print("Installing:", ", ".join(missing))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", *missing])

ensure_packages()

import mss
from PIL import Image, ImageChops
import fitz, ocrmypdf

def load_config():
    data = DEFAULTS.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f: data.update(json.load(f))
        except Exception: pass
    return data

def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception: pass

def find_tesseract():
    paths = [r"C:\Program Files\Tesseract-OCR\tesseract.exe",
             r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
             str(Path.home() / "AppData/Local/Programs/Tesseract-OCR/tesseract.exe"),
             str(Path.home() / "AppData/Local/Tesseract-OCR/tesseract.exe")]
    return next((p for p in paths if Path(p).exists()), None)

def install_tesseract():
    try:
        subprocess.run(["winget", "install", "--id", "UB-Mannheim.TesseractOCR", "--exact", "--silent",
                       "--accept-package-agreements", "--accept-source-agreements"], check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return True
    except Exception: return False

def similar(previous, current, threshold):
    if previous.size != current.size: return False
    diff = ImageChops.difference(previous.convert("L"), current.convert("L")).histogram()
    return 1 - sum(diff[16:]) / (previous.size[0] * previous.size[1]) >= threshold

def capture(region, path):
    with mss.mss() as sct:
        shot = sct.grab(region)
    image = Image.frombytes("RGB", shot.size, shot.rgb)
    image.save(path, "PNG", optimize=True)
    return image

def split_double_page(image, session, page):
    width, height = image.size
    middle = width // 2
    left = session / f"page_{page:04d}_left.png"
    right = session / f"page_{page:04d}_right.png"
    image.crop((0, 0, middle, height)).save(left, "PNG", optimize=True)
    image.crop((middle, 0, width, height)).save(right, "PNG", optimize=True)
    return [left, right]

def build_pdf(images, output):
    doc = fitz.open()
    for image in images:
        with Image.open(image) as img: width, height = img.size
        scale = min(1, 2000 / width)
        page = doc.new_page(width=width * scale, height=height * scale)
        page.insert_image(page.rect, filename=str(image), keep_proportion=True)
    doc.save(str(output), garbage=4, deflate=True)
    doc.close()

def run_ocr(image_pdf, output_pdf, language="deu+eng"):
    ocrmypdf.ocr(input_filename=str(image_pdf), output_filename=str(output_pdf),
                 language=language, deskew=False, rotate_pages=False, clean=False,
                 optimize=1, force_ocr=True, progress_bar=False)

def new_session(base_dir):
    session = Path(base_dir) / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session.mkdir(parents=True, exist_ok=True)
    return session
