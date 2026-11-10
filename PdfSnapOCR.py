# -*- coding: utf-8 -*-
"""
PdfSnapOCR

Automatische PDF-Seiten-Screenshots mit optionaler OCR-Textebene.

- Unabhängig vom PDF-Reader
- Einzelseiten- und Doppelseitenmodus
- Automatisches Weiterblättern
- Automatischer Stopp bei unveränderter Seite
- Automatische PDF-Erstellung
- Optionale OCR-Textebene
- Automatische Installation der Python-Pakete
"""

import os
import sys
import subprocess
import importlib
import threading
import time
import json
import traceback
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

REQUIRED_PACKAGES = [
    "mss",
    "pillow",
    "pymupdf",
    "keyboard",
    "ocrmypdf",
]

APP_NAME = "PdfSnapOCR"
CONFIG_FILE = Path(__file__).with_name("pdfsnapocr_config.json")

DEFAULT_CONFIG = {
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
}


def ensure_packages():
    missing = []

    for package in REQUIRED_PACKAGES:
        try:
            importlib.import_module(package)
        except ImportError:
            missing.append(package)

    if missing:
        print("Installiere fehlende Pakete:", ", ".join(missing))
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", *missing]
        )


ensure_packages()

import mss
import keyboard
from PIL import Image, ImageChops
import fitz
import ocrmypdf


def load_config():
    config = DEFAULT_CONFIG.copy()

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                config.update(json.load(file))
        except Exception:
            pass

    return config


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=2, ensure_ascii=False)
    except Exception:
        pass


def find_tesseract():
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        str(Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe"),
        str(Path.home() / "AppData" / "Local" / "Tesseract-OCR" / "tesseract.exe"),
    ]

    for candidate in candidates:
        if Path(candidate).exists():
            return candidate

    return None


def install_tesseract():
    try:
        subprocess.run(
            [
                "winget", "install",
                "--id", "UB-Mannheim.TesseractOCR",
                "--exact",
                "--silent",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return True
    except Exception:
        return False


class RegionSelector(tk.Tk):
    def __init__(self):
        super().__init__()

        self.result_region = None

        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.22)
        self.configure(background="black")

        self.canvas = tk.Canvas(
            self,
            bg="black",
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True)

        self.start = None
        self.rect = None

        info = tk.Label(
            self.canvas,
            text=(
                "PDF-Seitenbereich aufziehen\n\n"
                "Einzelseite: nur eine PDF-Seite markieren\n"
                "Doppelseite: beide Seiten gemeinsam markieren\n\n"
                "ESC = Abbrechen"
            ),
            bg="#101418",
            fg="#dce6f2",
            font=("Segoe UI", 13, "bold"),
            padx=26,
            pady=18,
        )
        info.place(relx=0.5, rely=0.08, anchor="center")

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda event: self.destroy())

    def on_press(self, event):
        self.start = (event.x_root, event.y_root)

        if self.rect:
            self.canvas.delete(self.rect)

        self.rect = self.canvas.create_rectangle(
            event.x, event.y,
            event.x, event.y,
            outline="#00c8ff",
            width=3,
        )

    def on_drag(self, event):
        if self.start:
            self.canvas.coords(
                self.rect,
                self.start[0], self.start[1],
                event.x_root, event.y_root,
            )

    def on_release(self, event):
        if not self.start:
            return

        x1, y1 = self.start
        x2, y2 = event.x_root, event.y_root

        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))

        if right - left >= 40 and bottom - top >= 40:
            self.result_region = {
                "left": int(left),
                "top": int(top),
                "width": int(right - left),
                "height": int(bottom - top),
            }

        self.destroy()


def images_similar(previous, current, threshold):
    if previous.size != current.size:
        return False

    diff = ImageChops.difference(
        previous.convert("L"),
        current.convert("L"),
    )

    histogram = diff.histogram()
    changed_pixels = sum(histogram[16:])
    total_pixels = previous.size[0] * previous.size[1]

    similarity = 1.0 - (changed_pixels / total_pixels)
    return similarity >= threshold


class PdfSnapOCRApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.config_data = load_config()
        self.region = None
        self.capture_thread = None
        self.stop_event = threading.Event()
        self.running = False

        self.title("PdfSnapOCR")
        self.geometry("1100x760")
        self.minsize(960, 680)
        self.configure(background="#12161c")

        self._build_style()
        self._build_ui()
        self._load_settings()
        self._update_tesseract_status()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_style(self):
        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background="#12161c")
        style.configure("TLabel", background="#12161c", foreground="#dbe4ee")

        style.configure(
            "Title.TLabel",
            background="#12161c",
            foreground="#7fd1ff",
            font=("Segoe UI", 22, "bold"),
        )

        style.configure(
            "Subtitle.TLabel",
            background="#12161c",
            foreground="#9fb0c2",
            font=("Segoe UI", 10),
        )

        style.configure(
            "Section.TLabelframe",
            background="#181e26",
            borderwidth=1,
            relief="solid",
        )

        style.configure(
            "Section.TLabelframe.Label",
            background="#181e26",
            foreground="#8fd3ff",
            font=("Segoe UI", 10, "bold"),
        )

        style.configure(
            "TButton",
            background="#243040",
            foreground="#eaf2fb",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            padding=10,
        )

        style.map(
            "TButton",
            background=[("active", "#2f4156")],
            foreground=[("disabled", "#7d8794")],
        )

        style.configure(
            "Primary.TButton",
            background="#0078d4",
            foreground="white",
        )

        style.map(
            "Primary.TButton",
            background=[
                ("active", "#1887dd"),
                ("disabled", "#28475e"),
            ],
        )

        style.configure(
            "Danger.TButton",
            background="#b3382f",
            foreground="white",
        )

        style.map(
            "Danger.TButton",
            background=[
                ("active", "#cc4a3f"),
                ("disabled", "#5d2b28"),
            ],
        )

        style.configure(
            "TEntry",
            fieldbackground="#20262f",
            foreground="#eaf2fb",
            insertcolor="#eaf2fb",
        )

        style.configure(
            "TCombobox",
            fieldbackground="#20262f",
            background="#20262f",
            foreground="#eaf2fb",
        )

        style.configure(
            "TCheckbutton",
            background="#181e26",
            foreground="#dbe4ee",
        )

        style.configure("TScale", background="#181e26")

        style.configure(
            "Horizontal.TProgressbar",
            background="#00c8ff",
            troughcolor="#20262f",
            borderwidth=0,
        )

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=(20, 18, 20, 8))
        header.grid(row=0, column=0, sticky="ew")

        ttk.Label(header, text="PdfSnapOCR", style="Title.TLabel").pack(anchor="w")

        ttk.Label(
            header,
            text="Automatische PDF-Seiten-Screenshots · Einzelseite / Doppelseite · OCR-PDF",
            style="Subtitle.TLabel",
        ).pack(anchor="w")

        main = ttk.Frame(self, padding=(20, 0, 20, 12))
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left = ttk.Labelframe(
            main,
            text=" Aufnahme ",
            style="Section.TLabelframe",
            padding=18,
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.columnconfigure(1, weight=1)

        ttk.Label(left, text="Seitenmodus").grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.page_mode = ttk.Combobox(
            left,
            values=["Einzelseite", "Doppelseite"],
            state="readonly",
            width=24,
        )
        self.page_mode.grid(row=0, column=1, sticky="ew", pady=(0, 12))

        ttk.Label(left, text="Blättertaste").grid(row=1, column=0, sticky="w", pady=(0, 4))

        self.turn_key = ttk.Combobox(
            left,
            values=["pagedown", "right", "space", "down"],
            state="readonly",
            width=24,
        )
        self.turn_key.grid(row=1, column=1, sticky="ew", pady=(0, 12))

        ttk.Label(left, text="Wartezeit nach Blättern").grid(
            row=2, column=0, sticky="w", pady=(0, 4)
        )

        self.delay_after_turn = tk.DoubleVar()
        ttk.Scale(
            left,
            from_=0.2,
            to=5.0,
            variable=self.delay_after_turn,
            orient="horizontal",
            command=lambda value: self._update_slider_labels(),
        ).grid(row=2, column=1, sticky="ew", pady=(0, 2))

        self.delay_after_turn_label = ttk.Label(left, text="")
        self.delay_after_turn_label.grid(row=3, column=1, sticky="w", pady=(0, 12))

        ttk.Label(left, text="Wartezeit vor Screenshot").grid(
            row=4, column=0, sticky="w", pady=(0, 4)
        )

        self.delay_before_capture = tk.DoubleVar()
        ttk.Scale(
            left,
            from_=0.0,
            to=3.0,
            variable=self.delay_before_capture,
            orient="horizontal",
            command=lambda value: self._update_slider_labels(),
        ).grid(row=4, column=1, sticky="ew", pady=(0, 2))

        self.delay_before_capture_label = ttk.Label(left, text="")
        self.delay_before_capture_label.grid(row=5, column=1, sticky="w", pady=(0, 12))

        ttk.Label(left, text="Maximale Seitenzahl").grid(
            row=6, column=0, sticky="w", pady=(0, 4)
        )

        self.max_pages = ttk.Spinbox(left, from_=1, to=2000, width=10)
        self.max_pages.grid(row=6, column=1, sticky="w", pady=(0, 12))

        self.auto_stop_var = tk.BooleanVar()
        ttk.Checkbutton(
            left,
            text="Automatisch stoppen, wenn sich die Seite nicht mehr ändert",
            variable=self.auto_stop_var,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Label(left, text="Ähnlichkeitsschwelle").grid(
            row=8, column=0, sticky="w", pady=(0, 4)
        )

        self.change_threshold = tk.DoubleVar()
        ttk.Scale(
            left,
            from_=0.90,
            to=0.999,
            variable=self.change_threshold,
            orient="horizontal",
            command=lambda value: self._update_slider_labels(),
        ).grid(row=8, column=1, sticky="ew", pady=(0, 2))

        self.change_threshold_label = ttk.Label(left, text="")
        self.change_threshold_label.grid(row=9, column=1, sticky="w", pady=(0, 12))

        ttk.Button(
            left,
            text="🔍 Seitenbereich auswählen",
            command=self.select_region,
            style="Primary.TButton",
        ).grid(row=10, column=0, columnspan=2, sticky="ew", pady=(8, 6))

        self.region_label = ttk.Label(
            left,
            text="Noch kein Bereich ausgewählt.",
            foreground="#9fb0c2",
            wraplength=380,
        )
        self.region_label.grid(row=11, column=0, columnspan=2, sticky="w", pady=(0, 10))

        right = ttk.Labelframe(
            main,
            text=" OCR & Ausgabe ",
            style="Section.TLabelframe",
            padding=18,
        )
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(1, weight=1)

        ttk.Label(right, text="Ausgabeordner").grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.output_dir = ttk.Entry(right)
        self.output_dir.grid(row=0, column=1, sticky="ew", pady=(0, 4))

        ttk.Button(
            right,
            text="Auswählen",
            command=self.choose_output_dir,
        ).grid(row=0, column=2, padx=(8, 0))

        ttk.Label(right, text="OCR-Sprache").grid(row=1, column=0, sticky="w", pady=(14, 4))

        self.ocr_language = ttk.Combobox(
            right,
            values=["deu+eng", "deu", "eng", "fra", "ita", "spa"],
            state="readonly",
            width=24,
        )
        self.ocr_language.grid(row=1, column=1, sticky="w", pady=(0, 12))

        self.ocr_enabled = tk.BooleanVar()
        ttk.Checkbutton(
            right,
            text="OCR-Textebene erstellen, falls Tesseract verfügbar ist",
            variable=self.ocr_enabled,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(
            right,
            text=(
                "Die OCR macht die PDF durchsuchbar und Text kopierbar.\n"
                "Das sichtbare Design bleibt als Screenshot-Bild erhalten."
            ),
            foreground="#9fb0c2",
            wraplength=360,
            justify="left",
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(0, 14))

        ttk.Button(
            right,
            text="Tesseract prüfen / installieren",
            command=self.check_or_install_tesseract,
        ).grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self.tesseract_label = ttk.Label(
            right,
            text="",
            foreground="#9fb0c2",
            wraplength=360,
        )
        self.tesseract_label.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 10))

        actions = ttk.Frame(self, padding=(20, 0, 20, 10))
        actions.grid(row=2, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.columnconfigure(2, weight=1)

        self.start_button = ttk.Button(
            actions,
            text="▶ Automatische Aufnahme starten",
            command=self.start_capture,
            style="Primary.TButton",
        )
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.stop_button = ttk.Button(
            actions,
            text="⏹ Aufnahme stoppen",
            command=self.stop_capture,
            style="Danger.TButton",
            state="disabled",
        )
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        ttk.Button(
            actions,
            text="📂 Ausgabeordner öffnen",
            command=self.open_output_dir,
        ).grid(row=0, column=2, sticky="ew")

        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.progress.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 8))

        log_frame = ttk.Labelframe(
            self,
            text=" Protokoll ",
            style="Section.TLabelframe",
            padding=12,
        )
        log_frame.grid(row=4, column=0, sticky="nsew", padx=20, pady=(0, 20))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log = tk.Text(
            log_frame,
            height=12,
            bg="#0d1117",
            fg="#c9d6e3",
            insertbackground="#c9d6e3",
            relief="flat",
            font=("Consolas", 9),
        )
        self.log.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

        self.bind("<F9>", lambda event: self.stop_capture())

    def _load_settings(self):
        self.page_mode.set(
            "Einzelseite" if self.config_data["page_mode"] == "single" else "Doppelseite"
        )

        self.turn_key.set(self.config_data["turn_key"])
        self.delay_after_turn.set(self.config_data["delay_after_turn"])
        self.delay_before_capture.set(self.config_data["delay_before_capture"])
        self.max_pages.set(self.config_data["max_pages"])
        self.auto_stop_var.set(self.config_data["auto_stop"])
        self.change_threshold.set(self.config_data["change_threshold"])
        self.ocr_enabled.set(self.config_data["ocr_enabled"])
        self.ocr_language.set(self.config_data["ocr_language"])
        self.output_dir.insert(0, self.config_data["output_dir"])

        self._update_slider_labels()

    def _update_slider_labels(self):
        self.delay_after_turn_label.config(
            text=f"{self.delay_after_turn.get():.1f} Sekunden"
        )

        self.delay_before_capture_label.config(
            text=f"{self.delay_before_capture.get():.1f} Sekunden"
        )

        self.change_threshold_label.config(
            text=f"{self.change_threshold.get() * 100:.1f} % Ähnlichkeit"
        )

    def _collect_settings(self):
        self.config_data.update(
            {
                "output_dir": self.output_dir.get().strip()
                or str(Path.home() / "Documents" / "PdfSnapOCR"),
                "page_mode": "single" if self.page_mode.get() == "Einzelseite" else "double",
                "turn_key": self.turn_key.get(),
                "delay_after_turn": round(float(self.delay_after_turn.get()), 2),
                "delay_before_capture": round(float(self.delay_before_capture.get()), 2),
                "max_pages": int(self.max_pages.get()),
                "auto_stop": bool(self.auto_stop_var.get()),
                "change_threshold": round(float(self.change_threshold.get()), 3),
                "ocr_enabled": bool(self.ocr_enabled.get()),
                "ocr_language": self.ocr_language.get(),
            }
        )

        save_config(self.config_data)
        return self.config_data

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{timestamp}] {message}\n")
        self.log.see("end")

    def select_region(self):
        selector = RegionSelector()
        selector.mainloop()

        region = selector.result_region

        if not region:
            self.log_message("Kein Bereich ausgewählt.")
            return

        self.region = region

        self.region_label.config(
            text=(
                f"Bereich: {region['width']} × {region['height']} Pixel\n"
                f"Position: x={region['left']}, y={region['top']}"
            )
        )

        self.log_message(
            f"Bereich gesetzt: {region['width']} × {region['height']} Pixel."
        )

        if self.page_mode.get() == "Doppelseite":
            self.log_message(
                "Doppelseitenmodus aktiv. Der Bereich wird automatisch in linke und rechte Seite geteilt."
            )

    def choose_output_dir(self):
        directory = filedialog.askdirectory(
            title="Ausgabeordner wählen",
            initialdir=self.output_dir.get(),
        )

        if directory:
            self.output_dir.delete(0, "end")
            self.output_dir.insert(0, directory)

    def open_output_dir(self):
        path = Path(self.output_dir.get())

        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        if os.name == "nt":
            os.startfile(str(path))
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def check_or_install_tesseract(self):
        tesseract = find_tesseract()

        if tesseract:
            self.tesseract_label.config(
                text=f"Tesseract gefunden:\n{tesseract}",
                foreground="#7ee787",
            )
            self.log_message(f"Tesseract gefunden: {tesseract}")
            return

        self.log_message(
            "Tesseract nicht gefunden. Installation über winget wird versucht …"
        )

        if install_tesseract():
            tesseract = find_tesseract()

            if tesseract:
                self.tesseract_label.config(
                    text=f"Tesseract installiert:\n{tesseract}",
                    foreground="#7ee787",
                )
                self.log_message("Tesseract erfolgreich installiert.")
                return

        self.tesseract_label.config(
            text=(
                "Tesseract konnte nicht automatisch installiert werden.\n"
                "Bitte manuell installieren:\n"
                "https://github.com/UB-Mannheim/tesseract/wiki"
            ),
            foreground="#ffb86b",
        )

        self.log_message("Tesseract-Installation nicht erfolgreich.")

    def _update_tesseract_status(self):
        tesseract = find_tesseract()

        if tesseract:
            self.tesseract_label.config(
                text=f"Tesseract gefunden:\n{tesseract}",
                foreground="#7ee787",
            )
        else:
            self.tesseract_label.config(
                text=(
                    "Tesseract nicht gefunden.\n"
                    "OCR kann nach der Installation aktiviert werden."
                ),
                foreground="#ffb86b",
            )

    def start_capture(self):
        if self.running:
            return

        if self.region is None:
            messagebox.showwarning(
                APP_NAME,
                "Bitte zuerst den Seitenbereich auswählen.",
            )
            return

        settings = self._collect_settings()

        output_dir = Path(settings["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        session_dir = output_dir / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        session_dir.mkdir(parents=True, exist_ok=True)

        self.stop_event.clear()
        self.running = True

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress.config(value=0)

        self.log_message("Automatische Aufnahme gestartet.")
        self.log_message(f"Sitzungsordner: {session_dir}")

        self.capture_thread = threading.Thread(
            target=self._capture_worker,
            args=(settings, session_dir),
            daemon=True,
        )
        self.capture_thread.start()

    def stop_capture(self):
        if not self.running:
            return

        self.stop_event.set()
        self.log_message("Stopp angefordert.")

    def _capture_worker(self, settings, session_dir):
        try:
            captures = []
            previous_image = None

            turn_key = settings["turn_key"]
            page_mode = settings["page_mode"]
            max_pages = settings["max_pages"]
            delay_after_turn = settings["delay_after_turn"]
            delay_before_capture = settings["delay_before_capture"]
            auto_stop = settings["auto_stop"]
            threshold = settings["change_threshold"]

            page_index = 0

            while not self.stop_event.is_set() and page_index < max_pages:
                if delay_before_capture > 0:
                    time.sleep(delay_before_capture)

                if self.stop_event.is_set():
                    break

                page_index += 1
                screenshot_path = session_dir / f"page_{page_index:04d}.png"

                self.after(
                    0,
                    lambda i=page_index: self.log_message(
                        f"Screenshot {i} wird aufgenommen …"
                    ),
                )

                image = self._take_screenshot(self.region, screenshot_path)

                if image is None:
                    self.after(
                        0,
                        lambda: self.log_message(
                            "Screenshot fehlgeschlagen. Aufnahme wird gestoppt."
                        ),
                    )
                    break

                if page_mode == "single":
                    captures.append(screenshot_path)

                else:
                    left_path = session_dir / f"page_{page_index:04d}_left.png"
                    right_path = session_dir / f"page_{page_index:04d}_right.png"

                    width, height = image.size
                    middle = width // 2

                    left_image = image.crop((0, 0, middle, height))
                    right_image = image.crop((middle, 0, width, height))

                    left_image.save(left_path, "PNG", optimize=True)
                    right_image.save(right_path, "PNG", optimize=True)

                    captures.extend([left_path, right_path])

                self.after(
                    0,
                    lambda i=page_index, p=screenshot_path: self.log_message(
                        f"Screenshot {i} gespeichert: {p.name}"
                    ),
                )

                progress = min(100, int((page_index / max_pages) * 100))
                self.after(
                    0,
                    lambda value=progress: self.progress.config(value=value),
                )

                if auto_stop and previous_image is not None:
                    if images_similar(previous_image, image, threshold):
                        self.after(
                            0,
                            lambda: self.log_message(
                                "Seite hat sich nach dem Blättern nicht verändert. Automatischer Stopp."
                            ),
                        )
                        break

                previous_image = image

                if page_index >= max_pages:
                    break

                self.after(
                    0,
                    lambda: self.log_message("Blättere zur nächsten Seite …"),
                )

                try:
                    keyboard.press_and_release(turn_key)
                except Exception as exc:
                    self.after(
                        0,
                        lambda error=exc: self.log_message(
                            f"Blättern fehlgeschlagen: {error}"
                        ),
                    )
                    break

                time.sleep(delay_after_turn)

            if captures:
                self.after(
                    0,
                    lambda count=len(captures): self.log_message(
                        f"{count} PDF-Seiten erfasst. Erstelle PDF …"
                    ),
                )

                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                base_name = f"PDF_Screenshot_{timestamp}"

                image_pdf = session_dir / f"{base_name}_image.pdf"
                final_pdf = session_dir / f"{base_name}_ocr.pdf"

                self._build_pdf(captures, image_pdf)

                self.after(
                    0,
                    lambda path=image_pdf: self.log_message(
                        f"Bild-PDF erstellt: {path.name}"
                    ),
                )

                if settings["ocr_enabled"]:
                    tesseract = find_tesseract()

                    if tesseract:
                        self.after(
                            0,
                            lambda: self.log_message("Starte OCR …"),
                        )

                        try:
                            ocrmypdf.ocr(
                                input_filename=str(image_pdf),
                                output_filename=str(final_pdf),
                                language=settings["ocr_language"],
                                deskew=False,
                                rotate_pages=False,
                                clean=False,
                                optimize=1,
                                force_ocr=True,
                                progress_bar=False,
                            )

                            self.after(
                                0,
                                lambda path=final_pdf: self.log_message(
                                    f"OCR-PDF erstellt: {path.name}"
                                ),
                            )

                        except Exception as exc:
                            self.after(
                                0,
                                lambda error=exc: self.log_message(
                                    f"OCR fehlgeschlagen: {error}"
                                ),
                            )

                    else:
                        self.after(
                            0,
                            lambda: self.log_message(
                                "OCR übersprungen: Tesseract wurde nicht gefunden."
                            ),
                        )

                self.after(
                    0,
                    lambda: self.log_message(
                        "Aufnahme und PDF-Erstellung abgeschlossen."
                    ),
                )

        except Exception as exc:
            error = traceback.format_exc()

            self.after(
                0,
                lambda: self.log_message(f"Kritischer Fehler:\n{error}"),
            )

        finally:
            self.running = False

            self.after(
                0,
                lambda: self.start_button.config(state="normal"),
            )

            self.after(
                0,
                lambda: self.stop_button.config(state="disabled"),
            )

    def _take_screenshot(self, region, output_path):
        try:
            with mss.mss() as sct:
                screenshot = sct.grab(region)

            image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            image.save(output_path, "PNG", optimize=True)

            return image

        except Exception:
            return None

    def _build_pdf(self, image_paths, output_path):
        doc = fitz.open()

        for image_path in image_paths:
            with Image.open(image_path) as image:
                width, height = image.size

            scale = min(1.0, 2000 / width)
            page_width = width * scale
            page_height = height * scale

            page = doc.new_page(width=page_width, height=page_height)
            page.insert_image(
                page.rect,
                filename=str(image_path),
                keep_proportion=True,
            )

        doc.save(str(output_path), garbage=4, deflate=True)
        doc.close()

    def on_close(self):
        if self.running:
            if not messagebox.askyesno(
                APP_NAME,
                "Eine Aufnahme läuft. Trotzdem beenden?",
            ):
                return

            self.stop_event.set()

        self._collect_settings()
        self.destroy()


def main():
    app = PdfSnapOCRApp()
    app.mainloop()


if __name__ == "__main__":
    main()
