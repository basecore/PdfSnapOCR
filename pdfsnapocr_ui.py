# -*- coding: utf-8 -*-
"""Light UI builder for PdfSnapOCR."""

import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog

from pdfsnapocr_frames import FrameSelector
from pdfsnapocr_core import find_tesseract, install_tesseract

def build_ui(app):
    app.title("PdfSnapOCR")
    app.geometry("1000x680")
    app.minsize(900, 620)
    app.configure(bg="#f3f6fb")

    s = ttk.Style(app)
    try: s.theme_use("clam")
    except Exception: pass
    s.configure("TFrame", background="#f3f6fb")
    s.configure("TLabel", background="#f3f6fb", foreground="#1f2937")
    s.configure("TButton", background="#e6ebf2", foreground="#1f2937", padding=8)
    s.map("TButton", background=[("active", "#d7e0ea")])
    s.configure("Primary.TButton", background="#2563eb", foreground="white")
    s.map("Primary.TButton", background=[("active", "#1d4ed8")])
    s.configure("Danger.TButton", background="#dc2626", foreground="white")
    s.map("Danger.TButton", background=[("active", "#b91c1c")])
    s.configure("Card.TLabelframe", background="white", borderwidth=1, relief="solid")
    s.configure("Card.TLabelframe.Label", background="white", foreground="#2563eb", font=("Segoe UI", 10, "bold"))

    main = ttk.Frame(app, padding=16)
    main.grid(row=0, column=0, sticky="nsew")
    app.columnconfigure(0, weight=1)
    app.rowconfigure(1, weight=1)
    main.columnconfigure(1, weight=1)

    ttk.Label(main, text="PdfSnapOCR", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
    ttk.Label(main, text="Automatische PDF-Seiten-Screenshots · Einzelseite / Doppelseite · OCR-PDF",
              foreground="#5b6b7c").grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

    ttk.Label(main, text="Seitenmodus").grid(row=2, column=0, sticky="w", pady=4)
    app.mode = ttk.Combobox(main, values=["Einzelseite", "Doppelseite"], state="readonly")
    app.mode.grid(row=2, column=1, sticky="ew", pady=4)

    ttk.Label(main, text="Blättertaste").grid(row=3, column=0, sticky="w", pady=4)
    app.key = ttk.Combobox(main, values=["pagedown", "right", "space", "down"], state="readonly")
    app.key.grid(row=3, column=1, sticky="ew", pady=4)

    ttk.Label(main, text="Wartezeit nach Blättern").grid(row=4, column=0, sticky="w", pady=4)
    app.after_turn = tk.DoubleVar()
    ttk.Scale(main, from_=.2, to=5, variable=app.after_turn, orient="horizontal",
              command=lambda v: labels(app)).grid(row=4, column=1, sticky="ew", pady=4)
    app.after_label = ttk.Label(main, text="")
    app.after_label.grid(row=4, column=2, sticky="w", pady=4)

    ttk.Label(main, text="Wartezeit vor Screenshot").grid(row=5, column=0, sticky="w", pady=4)
    app.before_capture = tk.DoubleVar()
    ttk.Scale(main, from_=0, to=3, variable=app.before_capture, orient="horizontal",
              command=lambda v: labels(app)).grid(row=5, column=1, sticky="ew", pady=4)
    app.before_label = ttk.Label(main, text="")
    app.before_label.grid(row=5, column=2, sticky="w", pady=4)

    ttk.Label(main, text="Maximale Seitenzahl").grid(row=6, column=0, sticky="w", pady=4)
    app.max_pages = ttk.Spinbox(main, from_=1, to=2000, width=8)
    app.max_pages.grid(row=6, column=1, sticky="w", pady=4)

    app.auto_stop = tk.BooleanVar()
    ttk.Checkbutton(main, text="Automatisch stoppen, wenn sich die Seite nicht mehr ändert",
                    variable=app.auto_stop).grid(row=7, column=0, columnspan=3, sticky="w", pady=4)

    ttk.Label(main, text="Ähnlichkeitsschwelle").grid(row=8, column=0, sticky="w", pady=4)
    app.threshold = tk.DoubleVar()
    ttk.Scale(main, from_=.9, to=.999, variable=app.threshold, orient="horizontal",
              command=lambda v: labels(app)).grid(row=8, column=1, sticky="ew", pady=4)
    app.threshold_label = ttk.Label(main, text="")
    app.threshold_label.grid(row=8, column=2, sticky="w", pady=4)

    ttk.Button(main, text="🔍 PDF-Bereich auswählen", command=lambda: select_region(app),
               style="Primary.TButton").grid(row=9, column=0, columnspan=3, sticky="ew", pady=8)

    app.region_label = tk.Label(main, justify="left", padx=12, pady=10, bg="#eff6ff", fg="#1e3a8a",
        text="Noch kein PDF-Bereich ausgewählt.\n\nKlicke auf „PDF-Bereich auswählen“ und lege\nden blauen Rahmen über die PDF-Seite.")
    app.region_label.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(0, 8))

    ttk.Label(main, text="Ausgabeordner").grid(row=11, column=0, sticky="w", pady=4)
    app.outdir = ttk.Entry(main)
    app.outdir.grid(row=11, column=1, sticky="ew", pady=4)
    ttk.Button(main, text="Auswählen", command=lambda: choose_dir(app)).grid(row=11, column=2, padx=(6, 0))

    ttk.Label(main, text="OCR-Sprache").grid(row=12, column=0, sticky="w", pady=4)
    app.language = ttk.Combobox(main, values=["deu+eng", "deu", "eng", "fra", "ita", "spa"], state="readonly")
    app.language.grid(row=12, column=1, sticky="w", pady=4)

    app.ocr_enabled = tk.BooleanVar()
    ttk.Checkbutton(main, text="OCR-Textebene erstellen, falls Tesseract verfügbar ist",
                    variable=app.ocr_enabled).grid(row=13, column=0, columnspan=3, sticky="w", pady=4)

    ttk.Button(main, text="Tesseract prüfen / installieren", command=lambda: tesseract_install(app)).grid(row=14, column=0, columnspan=3, sticky="ew", pady=6)
    app.tess_label = ttk.Label(main, foreground="#5b6b7c", wraplength=800)
    app.tess_label.grid(row=15, column=0, columnspan=3, sticky="w", pady=(0, 8))

    actions = ttk.Frame(main)
    actions.grid(row=16, column=0, columnspan=3, sticky="ew", pady=(6, 8))
    for i in range(3): actions.columnconfigure(i, weight=1)

    app.start_btn = ttk.Button(actions, text="▶ Automatische Aufnahme starten", command=app.start, style="Primary.TButton")
    app.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    app.stop_btn = ttk.Button(actions, text="⏹ Aufnahme stoppen", command=app.stop, style="Danger.TButton", state="disabled")
    app.stop_btn.grid(row=0, column=1, sticky="ew", padx=(0, 8))
    ttk.Button(actions, text="📂 Ausgabeordner öffnen", command=lambda: open_dir(app)).grid(row=0, column=2, sticky="ew")

    app.progress = ttk.Progressbar(main, maximum=100)
    app.progress.grid(row=17, column=0, columnspan=3, sticky="ew", pady=(0, 8))

    app.log = tk.Text(main, height=10, bg="white", fg="#1f2937", relief="flat", font=("Consolas", 9))
    app.log.grid(row=18, column=0, columnspan=3, sticky="nsew")
    app.bind("<F9>", lambda e: app.stop())

def labels(app):
    app.after_label.config(text=f"{app.after_turn.get():.1f} Sekunden")
    app.before_label.config(text=f"{app.before_capture.get():.1f} Sekunden")
    app.threshold_label.config(text=f"{app.threshold.get() * 100:.1f} % Ähnlichkeit")

def select_region(app):
    mode = "double" if app.mode.get() == "Doppelseite" else "single"
    selector = FrameSelector(app, mode)
    selector.grab_set()
    app.wait_window(selector)
    region = selector.result
    if not region:
        app.log("Kein Bereich ausgewählt.")
        return
    app.region = region
    text = "Doppelseitenmodus\nDer Bereich wird automatisch in linke und rechte Seite geteilt." if mode == "double" else "Einzelseitenmodus"
    app.region_label.config(text=f"{text}\n\nBereich: {region['width']} × {region['height']} Pixel\nPosition: x={region['left']}, y={region['top']}\n\nStelle nun die erste PDF-Seite in diesem Bereich dar.")
    app.log(f"Bereich gesetzt: {region['width']} × {region['height']} Pixel bei x={region['left']}, y={region['top']}.")

def choose_dir(app):
    path = filedialog.askdirectory(initialdir=app.outdir.get())
    if path:
        app.outdir.delete(0, "end")
        app.outdir.insert(0, path)

def open_dir(app):
    path = Path(app.outdir.get())
    path.mkdir(parents=True, exist_ok=True)
    os.startfile(str(path)) if os.name == "nt" else __import__("subprocess").Popen(["xdg-open", str(path)])

def tesseract_install(app):
    path = find_tesseract()
    if path:
        app.tess_label.config(text=f"Tesseract gefunden:\n{path}", foreground="#15803d")
        app.log(f"Tesseract gefunden: {path}")
        return
    app.log("Tesseract nicht gefunden. Installation über winget wird versucht …")
    if install_tesseract() and (path := find_tesseract()):
        app.tess_label.config(text=f"Tesseract installiert:\n{path}", foreground="#15803d")
        app.log("Tesseract erfolgreich installiert.")
        return
    app.tess_label.config(text="Tesseract konnte nicht automatisch installiert werden.\nhttps://github.com/UB-Mannheim/tesseract/wiki", foreground="#b45309")
    app.log("Tesseract-Installation nicht erfolgreich.")

def tess_status(app):
    path = find_tesseract()
    app.tess_label.config(text=f"Tesseract gefunden:\n{path}" if path else "Tesseract nicht gefunden.\nOCR kann nach der Installation aktiviert werden.",
                          foreground="#15803d" if path else "#b45309")
