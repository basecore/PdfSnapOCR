# -*- coding: utf-8 -*-
"""Core capture, PDF rasterization, OCR and configuration helpers for PdfSnapOCR."""
import os
import sys
import subprocess
import importlib
import json
import shutil
from pathlib import Path
from datetime import datetime

REQUIRED = ["mss", "pillow", "pymupdf", "keyboard", "ocrmypdf"]
APP_VERSION = "2.3.0"
RELEASE_DATE = "2026-11-10"
CONFIG_FILE = Path(__file__).with_name("pdfsnapocr_config.json")
DEFAULTS = {
    "output_dir": str(Path.home() / "Documents" / "PdfSnapOCR"),
    "page_mode": "single",
    "turn_key": "pagedown",
    "delay_after_turn": 1.0,
    "delay_before_capture": 0.4,
    "max_pages": 200,
    "auto_stop": True,
    "change_threshold": 0.985,
    "ocr_enabled": True,
    "ocr_language": "deu+eng",
    "tesseract_path": "",
    "pdf_render_dpi": 200,
}


def ensure_packages():
    missing = []
    for name in REQUIRED:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    if missing:
        print("Installing required Python packages:", ", ".join(missing))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", *missing])


ensure_packages()
import mss
from PIL import Image, ImageChops
import fitz
import ocrmypdf


def load_config():
    data = DEFAULTS.copy()
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as stream:
                stored = json.load(stream)
            if isinstance(stored, dict):
                data.update(stored)
        except Exception:
            pass
    return data


def save_config(data):
    try:
        with CONFIG_FILE.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
    except Exception:
        pass


def find_tesseract(custom_path=""):
    candidates = []
    custom = str(custom_path or "").strip().strip('"')
    if custom:
        path = Path(custom).expanduser()
        if path.is_dir():
            candidates.append(path / ("tesseract.exe" if os.name == "nt" else "tesseract"))
        else:
            candidates.append(path)
    found = shutil.which("tesseract")
    if found:
        candidates.append(Path(found))
    if os.name == "nt":
        candidates.extend([
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
            Path.home() / "AppData/Local/Programs/Tesseract-OCR/tesseract.exe",
            Path.home() / "AppData/Local/Tesseract-OCR/tesseract.exe",
        ])
    for candidate in candidates:
        try:
            if candidate.is_file():
                return str(candidate.resolve())
        except OSError:
            continue
    return None


def install_tesseract():
    if os.name != "nt":
        return False
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["winget", "install", "--id", "UB-Mannheim.TesseractOCR", "--exact", "--silent",
             "--accept-package-agreements", "--accept-source-agreements"],
            check=True, creationflags=flags,
        )
        return True
    except Exception:
        return False


def similar(previous, current, threshold):
    if previous.size != current.size:
        return False
    diff = ImageChops.difference(previous.convert("L"), current.convert("L")).histogram()
    changed = sum(diff[16:])
    return 1.0 - changed / (previous.size[0] * previous.size[1]) >= threshold


def capture(region, path):
    with mss.mss() as sct:
        shot = sct.grab(region)
    image = Image.frombytes("RGB", shot.size, shot.rgb)
    image.save(path, "PNG", optimize=True)
    return image


def split_double_page(image, session, page_number):
    width, height = image.size
    middle = width // 2
    left_path = Path(session) / f"page_{page_number:04d}_left.png"
    right_path = Path(session) / f"page_{page_number:04d}_right.png"
    image.crop((0, 0, middle, height)).save(left_path, "PNG", optimize=True)
    image.crop((middle, 0, width, height)).save(right_path, "PNG", optimize=True)
    return [left_path, right_path]


def build_pdf(images, output, progress_callback=None):
    """Create a lossless image PDF with PdfSnapOCR version/date metadata."""
    images = list(images)
    if not images:
        raise ValueError("Es wurden keine Screenshots zum Erstellen des Bild-PDFs übergeben.")
    document = fitz.open()
    try:
        total = len(images)
        for index, image_path in enumerate(images, start=1):
            with Image.open(image_path) as image:
                width, height = image.size
            scale = min(1.0, 2000.0 / max(1, width))
            page = document.new_page(width=width * scale, height=height * scale)
            page.insert_image(page.rect, filename=str(image_path), keep_proportion=True)
            if progress_callback:
                progress_callback(index, total)
        pdf_date = "D:" + datetime.now().strftime("%Y%m%d%H%M%S")
        document.set_metadata({
            "title": Path(output).stem,
            "creator": f"PdfSnapOCR v{APP_VERSION}",
            "producer": f"PdfSnapOCR v{APP_VERSION}",
            "creationDate": pdf_date,
            "modDate": pdf_date,
        })
        document.save(str(output), garbage=4, deflate=True)
    finally:
        document.close()



def pdf_page_count(input_pdf):
    with fitz.open(str(input_pdf)) as source:
        if source.needs_pass:
            raise ValueError("Das PDF ist passwortgeschützt. Bitte zuerst entsperren und erneut importieren.")
        return source.page_count


def render_pdf_to_pdf(input_pdf, output_pdf, dpi=200, progress_callback=None,
                      stop_event=None, partial_output_pdf=None):
    """Rasterize at the selected DPI and save completed pages as a partial PDF on stop."""
    dpi = int(dpi)
    if not 72 <= dpi <= 600:
        raise ValueError("DPI muss im Bereich von 72 bis 600 liegen.")
    source = fitz.open(str(input_pdf))
    rasterized = fitz.open()
    pages_rendered = 0
    total = 0
    cancelled = False
    saved_path = None
    try:
        if source.needs_pass:
            raise ValueError("Das PDF ist passwortgeschützt. Bitte zuerst entsperren und erneut importieren.")
        total = source.page_count
        if total < 1:
            raise ValueError("Das PDF enthält keine Seiten.")
        matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        for index in range(total):
            if stop_event is not None and stop_event.is_set():
                cancelled = True
                break
            source_page = source.load_page(index)
            source_rect = source_page.rect
            pixmap = source_page.get_pixmap(matrix=matrix, alpha=False, annots=True)
            page = rasterized.new_page(width=source_rect.width, height=source_rect.height)
            page.insert_image(page.rect, stream=pixmap.tobytes("png"), keep_proportion=False)
            pages_rendered += 1
            if progress_callback:
                progress_callback(pages_rendered, total)
        if pages_rendered < total and stop_event is not None and stop_event.is_set():
            cancelled = True
        if pages_rendered:
            saved_path = Path(partial_output_pdf) if cancelled and partial_output_pdf else Path(output_pdf)
            source_meta = source.metadata or {}
            allowed = ("title", "author", "subject", "keywords", "creator", "producer", "creationDate", "modDate", "trapped")
            metadata = {key: (source_meta.get(key, "") or "") for key in allowed}
            if not metadata["title"]:
                metadata["title"] = Path(input_pdf).stem
            pdf_date = "D:" + datetime.now().strftime("%Y%m%d%H%M%S")
            metadata.update(creator=f"PdfSnapOCR v{APP_VERSION}",
                            producer=f"PdfSnapOCR v{APP_VERSION}",
                            creationDate=pdf_date, modDate=pdf_date)
            rasterized.set_metadata(metadata)
            saved_path.parent.mkdir(parents=True, exist_ok=True)
            rasterized.save(str(saved_path), garbage=4, deflate=True)
        return {"pages_rendered": pages_rendered, "total_pages": total,
                "cancelled": cancelled, "output_pdf": str(saved_path) if saved_path else None}
    finally:
        rasterized.close()
        source.close()



def run_ocr(image_pdf, output_pdf, language="deu+eng"):
    """Create a searchable PDF. OCRmyPDF expects input and output as positional arguments."""
    return ocrmypdf.ocr(
        str(image_pdf), str(output_pdf), language=language,
        deskew=False, rotate_pages=False, clean=False, optimize=0,
        force_ocr=True, output_type="pdf", progress_bar=False,
        jobs=1, use_threads=True,
    )

def new_session(base_dir):
    session = Path(base_dir) / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    suffix = 1
    candidate = session
    while candidate.exists():
        candidate = Path(f"{session}_{suffix}")
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate
