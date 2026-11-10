# -*- coding: utf-8 -*-
"""Application logic for PdfSnapOCR."""

import threading, time, traceback
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

from pdfsnapocr_core import (load_config, save_config, find_tesseract,
                             similar, capture, split_double_page,
                             build_pdf, run_ocr, new_session)
from pdfsnapocr_ui import build_ui, labels, tess_status

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.region = None
        self.stop_event = threading.Event()
        self.running = False
        build_ui(self)
        self._load()
        tess_status(self)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _load(self):
        self.mode.set("Einzelseite" if self.cfg["page_mode"] == "single" else "Doppelseite")
        self.key.set(self.cfg["turn_key"])
        self.after_turn.set(self.cfg["delay_after_turn"])
        self.before_capture.set(self.cfg["delay_before_capture"])
        self.max_pages.set(self.cfg["max_pages"])
        self.auto_stop.set(self.cfg["auto_stop"])
        self.threshold.set(self.cfg["change_threshold"])
        self.ocr_enabled.set(self.cfg["ocr_enabled"])
        self.language.set(self.cfg["ocr_language"])
        self.outdir.insert(0, self.cfg["output_dir"])
        labels(self)

    def _save(self):
        self.cfg.update({
            "output_dir": self.outdir.get().strip() or str(Path.home() / "Documents/PdfSnapOCR"),
            "page_mode": "single" if self.mode.get() == "Einzelseite" else "double",
            "turn_key": self.key.get(),
            "delay_after_turn": round(float(self.after_turn.get()), 2),
            "delay_before_capture": round(float(self.before_capture.get()), 2),
            "max_pages": int(self.max_pages.get()),
            "auto_stop": bool(self.auto_stop.get()),
            "change_threshold": round(float(self.threshold.get()), 3),
            "ocr_enabled": bool(self.ocr_enabled.get()),
            "ocr_language": self.language.get(),
        })
        save_config(self.cfg)
        return self.cfg

    def log(self, text):
        self.log_box.insert("end", f"[{datetime.now():%H:%M:%S}] {text}\n")
        self.log_box.see("end")

    def start(self):
        if self.running:
            return
        if not self.region:
            messagebox.showwarning("PdfSnapOCR", "Bitte zuerst den PDF-Bereich auswählen.\n\nEinzelseite: Eine PDF-Seite markieren.\nDoppelseite: Beide Seiten gemeinsam markieren.")
            return
        cfg = self._save()
        session = new_session(cfg["output_dir"])
        self.stop_event.clear()
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress.config(value=0)
        self.log("Automatische Aufnahme gestartet.")
        self.log(f"Sitzungsordner: {session}")
        threading.Thread(target=self.worker, args=(cfg, session), daemon=True).start()

    def stop(self):
        if self.running:
            self.stop_event.set()
            self.log("Stopp angefordert.")

    def worker(self, cfg, session):
        try:
            captures, previous, page = [], None, 0
            while not self.stop_event.is_set() and page < cfg["max_pages"]:
                if cfg["delay_before_capture"] > 0:
                    time.sleep(cfg["delay_before_capture"])
                if self.stop_event.is_set():
                    break
                page += 1
                path = session / f"page_{page:04d}.png"
                self.after(0, lambda p=page: self.log(f"Screenshot {p} wird aufgenommen …"))
                image = capture(self.region, path)
                if not image:
                    self.after(0, lambda: self.log("Screenshot fehlgeschlagen."))
                    break
                if cfg["page_mode"] == "single":
                    captures.append(path)
                else:
                    captures += split_double_page(image, session, page)
                self.after(0, lambda p=page, f=path: self.log(f"Screenshot {p} gespeichert: {f.name}"))
                self.after(0, lambda v=min(100, int(page / cfg["max_pages"] * 100)): self.progress.config(value=v))
                if cfg["auto_stop"] and previous and similar(previous, image, cfg["change_threshold"]):
                    self.after(0, lambda: self.log("Seite hat sich nicht verändert. Automatischer Stopp."))
                    break
                previous = image
                if page >= cfg["max_pages"]:
                    break
                self.after(0, lambda: self.log("Blättere zur nächsten Seite …"))
                try:
                    import keyboard
                    keyboard.press_and_release(cfg["turn_key"])
                except Exception as e:
                    self.after(0, lambda e=e: self.log(f"Blättern fehlgeschlagen: {e}"))
                    break
                time.sleep(cfg["delay_after_turn"])
            if captures:
                self.after(0, lambda n=len(captures): self.log(f"{n} PDF-Seiten erfasst. Erstelle PDF …"))
                stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                image_pdf = session / f"PDF_Screenshot_{stamp}_image.pdf"
                ocr_pdf = session / f"PDF_Screenshot_{stamp}_ocr.pdf"
                build_pdf(captures, image_pdf)
                self.after(0, lambda p=image_pdf: self.log(f"Bild-PDF erstellt: {p.name}"))
                if cfg["ocr_enabled"]:
                    if find_tesseract():
                        self.after(0, lambda: self.log("Starte OCR …"))
                        try:
                            run_ocr(image_pdf, ocr_pdf, cfg["ocr_language"])
                            self.after(0, lambda p=ocr_pdf: self.log(f"OCR-PDF erstellt: {p.name}"))
                        except Exception as e:
                            self.after(0, lambda e=e: self.log(f"OCR fehlgeschlagen: {e}"))
                    else:
                        self.after(0, lambda: self.log("OCR übersprungen: Tesseract wurde nicht gefunden."))
                self.after(0, lambda: self.log("Aufnahme und PDF-Erstellung abgeschlossen."))
        except Exception:
            error = traceback.format_exc()
            self.after(0, lambda: self.log(f"Kritischer Fehler:\n{error}"))
        finally:
            self.running = False
            self.after(0, lambda: self.start_btn.config(state="normal"))
            self.after(0, lambda: self.stop_btn.config(state="disabled"))

    def close(self):
        if self.running and not messagebox.askyesno("PdfSnapOCR", "Eine Aufnahme läuft. Trotzdem beenden?"):
            return
        if self.running:
            self.stop_event.set()
        self._save()
        self.destroy()
