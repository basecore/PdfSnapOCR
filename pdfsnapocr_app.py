# -*- coding: utf-8 -*-
"""PdfSnapOCR controller: screenshot workflow and direct PDF rasterization workflow."""
from __future__ import annotations

import ctypes
import os
import queue
import re
import threading
import time
import subprocess
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import fitz
import keyboard
import mss
from PIL import Image, ImageDraw, ImageTk

from pdfsnapocr_core import (APP_VERSION, RELEASE_DATE, build_pdf, find_tesseract, install_tesseract, load_config,
                             new_session, pdf_page_count, render_pdf_to_pdf, run_ocr,
                             save_config, similar, split_double_page)
from pdfsnapocr_frames import FrameSelector
from pdfsnapocr_ui import build_ui, labels

DPI_PRESETS = {"Niedrig · 96 DPI": 96, "Niedrig · 150 DPI": 150, "Mittel · 200 DPI": 200, "Hoch · 300 DPI": 300, "Sehr hoch · 400 DPI": 400, "Maximal · 600 DPI": 600}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.app_version = APP_VERSION
        self.release_date = RELEASE_DATE
        self.cfg = load_config()
        self.region = None
        self.running = False
        self.stop_event = threading.Event()
        self.events = queue.Queue()
        self.session = None
        self.captures = []
        self.capture_count = 0
        self.previous = None
        self.target = None
        self.session_region = None
        self.session_mode = None
        self.current_stage = "ready"
        self.current_workflow = "screenshot"
        self.stage_started_at = None
        self.last_elapsed = -1
        self.can_resume = False
        self.preview_checked = False
        self.test_completed = False
        self.preview_window = None
        self.preview_original = None
        self.preview_photo = None
        self._preview_restore_zoomed = False
        self._toast_window = None
        self.pdf_path = ""
        self.pdf_page_index = 0
        self.pdf_page_count = 0
        self.pdf_preview_original = None
        self.pdf_preview_photo = None
        self._tesseract_installing = False
        self._close_when_idle = False
        self._closed = False

        build_ui(self)
        self.mode.set("Einzelseite" if self.cfg.get("page_mode") == "single" else "Doppelseite")
        self.key.set(self.cfg.get("turn_key", "pagedown"))
        self.after_turn.set(self.cfg.get("delay_after_turn", 1.0))
        self.before_capture.set(self.cfg.get("delay_before_capture", 0.4))
        self.max_pages.set(self.cfg.get("max_pages", 200))
        self.auto_stop.set(bool(self.cfg.get("auto_stop", True)))
        self.threshold.set(self.cfg.get("change_threshold", 0.985))
        self.ocr_enabled.set(bool(self.cfg.get("ocr_enabled", True)))
        self.language.set(self.cfg.get("ocr_language", "deu+eng"))
        self.outdir.insert(0, self.cfg.get("output_dir", str(Path.home() / "Documents" / "PdfSnapOCR")))
        self.tesseract_path_var.set(self.cfg.get("tesseract_path", ""))
        dpi = int(self.cfg.get("pdf_render_dpi", 200))
        self.pdf_resolution_var.set(next((label for label, value in DPI_PRESETS.items() if value == dpi), "Mittel · 200 DPI"))
        labels(self)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._reset_screenshot_steps()
        self._set_status("Bereit")
        self.refresh_tesseract_status()
        self.refresh_summaries()
        self._update_controls()
        self.after(100, self.drain)

    # ---------- common UI and configuration ----------
    def log(self, message):
        self.log_box.insert("end", f"[{datetime.now():%H:%M:%S}] {message}\n")
        self.log_box.see("end")

    def clear_log(self):
        self.log_box.delete("1.0", "end")

    def _set_status(self, message):
        self.status.configure(text=message)
        self.footer_status.configure(text=message)

    def refresh_summaries(self):
        output = self.outdir.get().strip() if hasattr(self, "outdir") else ""
        output = output or str(Path.home() / "Documents" / "PdfSnapOCR")
        if hasattr(self, "output_summary"):
            self.output_summary.configure(text=f"Ausgabe: {output}")
        if hasattr(self, "pdf_output_summary"):
            self.pdf_output_summary.configure(text=f"Zielordner: {output}")
        if hasattr(self, "pdf_ocr_summary"):
            state = "OCR wird nach dem Rendern ausgeführt." if self.ocr_enabled.get() else "OCR ist deaktiviert; Ausgabe enthält nur Seitenbilder."
            self.pdf_ocr_summary.configure(text=state)

    def _save(self):
        output_dir = self.outdir.get().strip() or str(Path.home() / "Documents" / "PdfSnapOCR")
        selected_dpi = DPI_PRESETS.get(self.pdf_resolution_var.get(), 200)
        self.cfg.update(
            output_dir=output_dir,
            page_mode="single" if self.mode.get() == "Einzelseite" else "double",
            turn_key=self.key.get(),
            delay_after_turn=max(0.2, float(self.after_turn.get())),
            delay_before_capture=max(0.0, float(self.before_capture.get())),
            max_pages=max(1, int(self.max_pages.get())),
            auto_stop=bool(self.auto_stop.get()),
            change_threshold=float(self.threshold.get()),
            ocr_enabled=bool(self.ocr_enabled.get()),
            ocr_language=self.language.get(),
            tesseract_path=self.tesseract_path_var.get().strip(),
            pdf_render_dpi=selected_dpi,
        )
        save_config(self.cfg)
        self.refresh_summaries()
        return dict(self.cfg)

    def _update_controls(self):
        busy = self.running
        has_region = self.region is not None
        self.region_btn.configure(state="disabled" if busy else "normal")
        self.preview_btn.configure(state="normal" if has_region and not busy else "disabled")
        self.test_btn.configure(state="normal" if has_region and not busy else "disabled")
        self.start_btn.configure(state="normal" if has_region and not busy else "disabled")
        self.resume_btn.configure(state="normal" if self.can_resume and not busy else "disabled")
        self.pdf_file_btn.configure(state="disabled" if busy else "normal")
        self.pdf_run_btn.configure(state="normal" if self.pdf_path and not busy else "disabled")
        self.pdf_prev_btn.configure(state="normal" if self.pdf_page_count > 1 and self.pdf_page_index > 0 and not busy else "disabled")
        self.pdf_next_btn.configure(state="normal" if self.pdf_page_count > 1 and self.pdf_page_index < self.pdf_page_count - 1 and not busy else "disabled")
        self.stop_btn.configure(state="normal" if busy and self.current_stage not in {"ocr", "pdf"} else "disabled")
        self.open_folder_btn.configure(state="normal")
        for widget in getattr(self, "setting_widgets", []):
            try:
                widget.state(["disabled"] if busy else ["!disabled"])
            except (AttributeError, tk.TclError):
                try:
                    widget.configure(state="disabled" if busy else "normal")
                except tk.TclError:
                    pass
        if self._tesseract_installing:
            self.tess_install_btn.configure(state="disabled")
        elif not busy:
            self.tess_install_btn.configure(state="normal")

    def _reset_screenshot_steps(self):
        for key, text in (("capture", "1  Aufnahme"), ("pdf", "2  Bild-PDF"), ("ocr", "3  OCR")):
            self.phase_widgets[key].configure(text=text, style="Step.TLabel")

    def _update_screenshot_steps(self, stage):
        done = {"pdf": {"capture"}, "ocr": {"capture", "pdf"}, "complete": {"capture", "pdf", "ocr"}}.get(stage, set())
        titles = {"capture": "Aufnahme", "pdf": "Bild-PDF", "ocr": "OCR"}
        for index, key in enumerate(("capture", "pdf", "ocr"), start=1):
            label = self.phase_widgets[key]
            if key in done:
                label.configure(text=f"✓  {titles[key]}", style="Step.Done.TLabel")
            elif key == stage:
                label.configure(text=f"{index}  {titles[key]} · aktiv", style="Step.Active.TLabel")
            else:
                label.configure(text=f"{index}  {titles[key]}", style="Step.TLabel")

    def _set_stage(self, data):
        workflow = data.get("workflow", self.current_workflow)
        key = data.get("key", "ready")
        self.current_workflow = workflow
        self.current_stage = key
        self.stage_started_at = time.monotonic() if key in {"capture", "pdf", "pdf_render", "ocr"} else None
        self.last_elapsed = -1
        mode = data.get("mode", "determinate")
        if workflow == "import":
            self.pdf_stage_label.configure(text=data.get("title", "Bereit"))
            self.pdf_progress_label.configure(text=data.get("progress_text", ""))
            self.pdf_timer_label.configure(text="")
            self.pdf_progress.stop()
            if mode == "indeterminate":
                self.pdf_progress.configure(mode="indeterminate", maximum=100, value=0)
                self.pdf_progress.start(12)
            else:
                self.pdf_progress.configure(mode="determinate", maximum=max(1, data.get("maximum", 100)), value=data.get("value", 0))
        else:
            self.stage_label.configure(text=data.get("title", "Bereit für die Aufnahme"))
            self.stage_detail.configure(text=data.get("detail", ""))
            self.progress_label.configure(text=data.get("progress_text", ""))
            self.timer_label.configure(text="")
            self.progress.stop()
            if mode == "indeterminate":
                self.progress.configure(mode="indeterminate", maximum=100, value=0)
                self.progress.start(12)
            else:
                self.progress.configure(mode="determinate", maximum=max(1, data.get("maximum", 100)), value=data.get("value", 0))
            if key in {"capture", "pdf", "ocr", "complete"}:
                self._update_screenshot_steps(key)
        self._set_status(data.get("title", "Bereit"))
        self._update_controls()

    def _update_elapsed(self):
        if self.stage_started_at is None or self.current_stage not in {"capture", "pdf", "pdf_render", "ocr"}:
            return
        elapsed = int(time.monotonic() - self.stage_started_at)
        if elapsed == self.last_elapsed:
            return
        self.last_elapsed = elapsed
        minutes, seconds = divmod(elapsed, 60)
        hours, minutes = divmod(minutes, 60)
        text = f"Laufzeit {hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"Laufzeit {minutes:02d}:{seconds:02d}"
        if self.current_workflow == "import":
            self.pdf_timer_label.configure(text=text)
        else:
            self.timer_label.configure(text=text)

    def drain(self):
        if self._closed:
            return
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.log(value)
                elif kind == "stage":
                    self._set_stage(value)
                elif kind == "capture_count":
                    self.progress_label.configure(text=f"{value['pages']} PDF-Seiten erfasst · Limit {value['limit']}")
                elif kind == "progress":
                    done, total = value["done"], value["total"]
                    workflow = value.get("workflow", self.current_workflow)
                    if workflow == "import":
                        self.pdf_progress.stop()
                        self.pdf_progress.configure(mode="determinate", maximum=max(1, total), value=done)
                        self.pdf_progress_label.configure(text=f"PDF-Rasterung: {done} von {total} Seiten")
                    else:
                        self.progress.stop()
                        self.progress.configure(mode="determinate", maximum=max(1, total), value=done)
                        self.progress_label.configure(text=f"Bild-PDF: {done} von {total} Seiten")
                elif kind == "test_done":
                    self.test_completed = True
                    self.step_test_status.configure(text=value)
                elif kind == "tesseract":
                    self._finish_tesseract(value)
                elif kind == "done":
                    message = value.get("message", "Vorgang beendet.") if isinstance(value, dict) else str(value)
                    self.can_resume = bool(value.get("can_resume", False)) if isinstance(value, dict) else False
                    self.running = False
                    self.stop_event.clear()
                    self._set_status(message)
                    if self.current_workflow == "import":
                        if self.current_stage != "complete":
                            self.pdf_stage_label.configure(text="Vorgang beendet")
                    elif self.current_stage not in {"complete", "ready"}:
                        self.stage_label.configure(text="Vorgang beendet")
                        self.stage_detail.configure(text=message)
                    elif self.current_stage == "ready":
                        self.stage_label.configure(text="Bereit")
                        self.stage_detail.configure(text=message)
                    self._update_controls()
                    if self._close_when_idle:
                        self._close_when_idle = False
                        self._save_config_safely()
                        self._closed = True
                        self.destroy()
                        return
        except queue.Empty:
            pass
        self._update_elapsed()
        if not self._closed:
            self.after(100, self.drain)

    # ---------- screenshot workflow ----------
    def show_toast(self, message, duration=2100):
        try:
            old = getattr(self, "_toast_window", None)
            if old is not None and old.winfo_exists():
                old.destroy()
            toast = tk.Toplevel(self)
            self._toast_window = toast
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            tk.Label(toast, text=message, bg="#172033", fg="white",
                     font=("Segoe UI", 9, "bold"), padx=12, pady=8).pack()
            toast.update_idletasks()
            x = self.winfo_rootx() + max(10, self.winfo_width() - toast.winfo_width() - 24)
            y = self.winfo_rooty() + 68
            toast.geometry(f"+{x}+{y}")
            toast.after(duration, lambda: self._close_toast(toast))
        except tk.TclError:
            pass

    def _close_toast(self, toast):
        try:
            if toast.winfo_exists():
                toast.destroy()
        except tk.TclError:
            pass

    def select_region(self):
        if self.running:
            return
        mode = "double" if self.mode.get() == "Doppelseite" else "single"
        selector = FrameSelector(self, mode)
        selector.grab_set()
        self.wait_window(selector)
        if not selector.result:
            self._set_status("Auswahl abgebrochen")
            return
        self.region = selector.result
        self.can_resume = False
        self.preview_checked = False
        self.test_completed = False
        width, height = self.region["width"], self.region["height"]
        effective_width = width if mode == "single" else width // 2
        self.region_label.configure(text=f"{width} × {height} px · x={self.region['left']}, y={self.region['top']}")
        self.resolution_hint.configure(text=(f"Doppelseite: ca. {effective_width} × {height} px/Seite."
                                             if mode == "double" else f"Native Aufnahme: {width} × {height} px."))
        self.step_preview_status.configure(text="Bereich gewählt")
        self.step_test_status.configure(text="Optional")
        self._set_status("Bereich festgelegt")
        self.log(f"Bereich gesetzt: {width} × {height} Pixel bei x={self.region['left']}, y={self.region['top']}.")
        self.show_toast("Bereich gewählt · Vorschau als Nächstes")
        self._update_controls()


    def shot(self, region):
        with mss.mss() as sct:
            raw = sct.grab(region)
        return Image.frombytes("RGB", raw.size, raw.rgb)

    def preview(self):
        if self.running or not self.region:
            return
        try:
            self._preview_restore_zoomed = str(self.state()) == "zoomed"
        except tk.TclError:
            self._preview_restore_zoomed = False
        self.withdraw()
        self.after(300, self._capture_preview)


    def _capture_preview(self):
        try:
            self.preview_original = self.shot(dict(self.region))
            if self.mode.get() == "Doppelseite":
                ImageDraw.Draw(self.preview_original).line(
                    (self.preview_original.width // 2, 0,
                     self.preview_original.width // 2, self.preview_original.height),
                    fill="#E11D48", width=max(2, self.preview_original.width // 900),
                )
            self.deiconify()
            if self._preview_restore_zoomed:
                self.state("zoomed")
            self.update_idletasks()
            if self.preview_window and self.preview_window.winfo_exists():
                self.preview_window.destroy()
            win = self.preview_window = tk.Toplevel(self)
            win.title("Screenshot-Vorschau")
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            win.geometry(f"{sw}x{sh}+0+0")
            try:
                win.state("zoomed")
            except tk.TclError:
                pass
            win.configure(bg="#101827")
            win.rowconfigure(0, weight=1)
            win.columnconfigure(0, weight=1)
            canvas = self.preview_canvas = tk.Canvas(win, bg="#101827", highlightthickness=0)
            canvas.grid(row=0, column=0, sticky="nsew")
            canvas.bind("<Configure>", self._draw_capture_preview)
            footer = ttk.Frame(win, padding=(12, 7))
            footer.grid(row=1, column=0, sticky="ew")
            footer.columnconfigure(0, weight=1)
            width, height = self.preview_original.size
            page_width = width if self.mode.get() == "Einzelseite" else width // 2
            self.preview_caption = ttk.Label(footer, text=f"{width} × {height} px · pro Seite ca. {page_width} × {height} px")
            self.preview_caption.grid(row=0, column=0, sticky="w", padx=(0, 10))
            ttk.Button(footer, text="Schließen", command=win.destroy).grid(row=0, column=1, sticky="e")
            win.bind("<Escape>", lambda _e: win.destroy())
            win.lift()
            win.focus_force()
            win.after(100, self._draw_capture_preview)
            if self._preview_restore_zoomed:
                self.after_idle(lambda: self.state("zoomed"))
            self.preview_checked = True
            self.step_preview_status.configure(text="Vorschau geprüft")
            self.log(f"Vollbild-Vorschau geöffnet: {width} × {height} px.")
        except Exception as exc:
            self.deiconify()
            if self._preview_restore_zoomed:
                try:
                    self.state("zoomed")
                except tk.TclError:
                    pass
            messagebox.showerror("Vorschau fehlgeschlagen", str(exc), parent=self)


    def _draw_capture_preview(self, _event=None):
        if not getattr(self, "preview_canvas", None) or not self.preview_original:
            return
        canvas = self.preview_canvas
        width, height = max(1, canvas.winfo_width()), max(1, canvas.winfo_height())
        source = self.preview_original
        scale = min(width / source.width, height / source.height)
        display_size = (max(1, int(source.width * scale)), max(1, int(source.height * scale)))
        resampling = getattr(Image, "Resampling", Image).LANCZOS
        display = source.resize(display_size, resampling)
        self.preview_photo = ImageTk.PhotoImage(display)
        canvas.delete("all")
        canvas.create_image(width // 2, height // 2, image=self.preview_photo, anchor="center")

    def start(self):
        self.prepare(test=False, resume=False)

    def resume(self):
        self.prepare(test=False, resume=True)

    def prepare(self, test=False, resume=False):
        if self.running:
            return
        if not self.region:
            messagebox.showwarning("Screenshot-Aufnahme", "Bitte zuerst den Aufnahmebereich auswählen.", parent=self)
            return
        if resume and (not self.session or not self.can_resume):
            messagebox.showinfo("Fortsetzen", "Es gibt aktuell keine pausierte Aufnahme zum Fortsetzen.", parent=self)
            return
        try:
            cfg = self._save()
        except (ValueError, tk.TclError):
            messagebox.showerror("Optionen", "Bitte gültige Wartezeiten und eine gültige Seitenzahl eingeben.", parent=self)
            return
        if not test and not resume:
            self.session = new_session(cfg["output_dir"])
            self.captures = []
            self.capture_count = 0
            self.previous = None
            self.session_region = dict(self.region)
            self.session_mode = cfg["page_mode"]
            self.can_resume = False
            self._reset_screenshot_steps()
        if resume and (dict(self.region) != self.session_region or cfg["page_mode"] != self.session_mode):
            messagebox.showerror("Fortsetzen", "Bereich und Seitenmodus müssen der pausierten Sitzung entsprechen.", parent=self)
            return
        self.current_workflow = "screenshot"
        self.running = True
        self.stop_event.clear()
        self._update_controls()
        self._set_stage({"workflow": "screenshot", "key": "countdown", "title": "PDF-Reader aktivieren",
                         "detail": "Wechsle innerhalb von 5 Sekunden zum PDF-Reader.", "mode": "determinate",
                         "maximum": 100, "value": 0, "progress_text": "Startvorbereitung"})
        self.stop_btn.configure(state="normal")
        self.log("Bitte jetzt den PDF-Reader aktivieren. In 5 Sekunden wird das aktive Fenster übernommen.")
        self.countdown(5, test, resume, cfg, dict(self.region))

    def countdown(self, seconds, test, resume, cfg, region):
        if self.stop_event.is_set():
            self.events.put(("done", {"message": "Start abgebrochen.", "can_resume": False}))
            return
        if seconds:
            self._set_status(f"PDF-Reader aktivieren: {seconds} s")
            self.after(1000, lambda: self.countdown(seconds - 1, test, resume, cfg, region))
            return
        if os.name == "nt":
            self.target = ctypes.windll.user32.GetForegroundWindow()
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(self.target, ctypes.byref(pid))
            if pid.value == os.getpid():
                self.log("Kein PDF-Reader ausgewählt: PdfSnapOCR hat noch den Fokus.")
                self.events.put(("done", {"message": "Reader aktivieren und erneut starten.", "can_resume": False}))
                return
        self._set_status("Blättertest läuft" if test else "Aufnahme läuft")
        threading.Thread(target=self.worker, args=(cfg, region, test, resume), daemon=True).start()

    def stop(self):
        if not self.running:
            return
        if self.current_stage in {"pdf", "ocr"}:
            self.log("Der aktuelle PDF-/OCR-Export wird sicher abgeschlossen.")
            self.stop_btn.configure(state="disabled")
            return
        self.stop_event.set()
        self.stop_btn.configure(state="disabled")
        if self.current_workflow == "import" and self.current_stage == "pdf_render":
            self.log("Stopp angefordert. Die aktuelle Seite wird beendet; fertige Seiten werden als Teil-PDF gespeichert und bei aktivierter OCR weiterverarbeitet.")
            self._set_status("Teilergebnis wird erstellt …")
        else:
            self.log("Stopp angefordert. Bereits erfasste Seiten werden exportiert.")
            self._set_status("Stopp angefordert …")


    def turn(self, cfg):
        if os.name == "nt" and self.target and ctypes.windll.user32.GetForegroundWindow() != self.target:
            raise RuntimeError("Fokus gewechselt. Reader aktivieren und danach ‚Aufnahme nach Pause fortsetzen‘ wählen.")
        keyboard.press_and_release(cfg["turn_key"])

    def changed(self, old, cfg, region):
        for attempt in range(3):
            if self.stop_event.wait(cfg["delay_after_turn"] + cfg["delay_before_capture"]):
                return None
            image = self.shot(region)
            if not similar(old, image, cfg["change_threshold"]):
                return image
            self.events.put(("log", f"Noch keine Bildänderung, Prüfung {attempt + 1}/3."))
        return None

    def worker(self, cfg, region, test, resume):
        reason = "Aufnahme beendet."
        can_resume = False
        try:
            if test:
                before = self.shot(region)
                self.turn(cfg)
                changed = self.changed(before, cfg, region)
                result = ("Blättertest erfolgreich: Bildänderung erkannt. Der Reader ist eine Seite weiter; ggf. zur Startseite zurückblättern."
                          if changed is not None else
                          "Blättertest ohne Bildänderung. Reader-Fokus, Taste und Wartezeit prüfen.")
                self.events.put(("test_done", result))
                self.events.put(("log", result))
                reason = "Blättertest abgeschlossen."
                return

            self.events.put(("stage", {"workflow": "screenshot", "key": "capture",
                "title": "Screenshots werden aufgenommen", "detail": "PDF-Reader im Vordergrund lassen. Seitenzahl wird laufend aktualisiert.",
                "mode": "indeterminate", "progress_text": "Warte auf Screenshot …"}))
            if resume and self.previous is not None:
                current = self.shot(region)
                if not similar(self.previous, current, cfg["change_threshold"]):
                    image = current
                else:
                    self.turn(cfg)
                    image = self.changed(self.previous, cfg, region)
            elif self.previous is None:
                if self.stop_event.wait(cfg["delay_before_capture"]):
                    reason = "Aufnahme vor dem ersten Screenshot gestoppt."
                    return
                image = self.shot(region)
            else:
                image = self.changed(self.previous, cfg, region)

            while not self.stop_event.is_set():
                if image is None:
                    if self.stop_event.is_set():
                        break
                    if cfg["auto_stop"]:
                        reason = "Pausiert: keine Bildänderung erkannt. Dokumentende oder Blättern prüfen; danach kann fortgesetzt werden."
                        can_resume = bool(self.captures)
                        self.events.put(("log", reason))
                        break
                    self.events.put(("log", "Noch keine Bildänderung. Die Aufnahme wartet weiter; zum Beenden ‚Vorgang stoppen‘ wählen."))
                    image = self.changed(self.previous, cfg, region)
                    continue

                self.capture_count += 1
                image_path = self.session / f"page_{self.capture_count:04d}.png"
                image.save(image_path, format="PNG", optimize=True)
                page_files = [image_path] if cfg["page_mode"] == "single" else split_double_page(image, self.session, self.capture_count)
                self.captures.extend(page_files)
                self.previous = image
                page_width = image.width if cfg["page_mode"] == "single" else image.width // 2
                if self.capture_count == 1:
                    self.events.put(("log", f"Native Screenshotgröße: {image.width} × {image.height} px; pro PDF-Seite etwa {page_width} × {image.height} px."))
                    if cfg["page_mode"] == "double":
                        self.events.put(("log", "Doppelseitenmodus teilt die Screenshot-Breite auf zwei PDF-Seiten."))
                self.events.put(("log", f"Screenshot {self.capture_count} gespeichert; {len(self.captures)} PDF-Seiten."))
                self.events.put(("capture_count", {"pages": len(self.captures), "limit": cfg["max_pages"]}))
                if len(self.captures) >= cfg["max_pages"]:
                    reason = f"Maximale Seitenzahl ({cfg['max_pages']}) erreicht."
                    break
                self.turn(cfg)
                image = self.changed(self.previous, cfg, region)

            if self.stop_event.is_set():
                reason = "Aufnahme gestoppt. Bereits erfasste Seiten werden exportiert."
                can_resume = bool(self.captures)
        except Exception as exc:
            reason = f"Pausiert: {exc}"
            can_resume = bool(self.captures)
            self.events.put(("log", reason))
        finally:
            if not test and self.captures:
                try:
                    image_pdf = self.session / "capture_image.pdf"
                    total = len(self.captures)
                    self.events.put(("stage", {"workflow": "screenshot", "key": "pdf",
                        "title": "Bild-PDF wird erstellt", "detail": f"{total} PNG-Seiten werden verlustfrei eingebettet.",
                        "mode": "determinate", "maximum": total, "value": 0,
                        "progress_text": f"Bild-PDF: 0 von {total} Seiten"}))
                    def report(done, count):
                        self.events.put(("progress", {"workflow": "screenshot", "done": done, "total": count}))
                    build_pdf(self.captures, image_pdf, progress_callback=report)
                    self.events.put(("log", f"Bild-PDF erstellt: {image_pdf}"))
                    if cfg["ocr_enabled"]:
                        tess = find_tesseract(cfg.get("tesseract_path", ""))
                        if not tess:
                            reason += " Tesseract wurde nicht gefunden; Bild-PDF ist vorhanden, OCR wurde übersprungen."
                            self.events.put(("log", "Tesseract nicht gefunden; OCR wurde übersprungen. Bild-PDF ist vorhanden."))
                        else:
                            os.environ["PATH"] = str(Path(tess).parent) + os.pathsep + os.environ.get("PATH", "")
                            ocr_pdf = self.session / "capture_ocr.pdf"
                            self.events.put(("stage", {"workflow": "screenshot", "key": "ocr",
                                "title": "OCR wird ausgeführt", "detail": f"OCRmyPDF verarbeitet {total} Seiten · Sprache {cfg['ocr_language']}.",
                                "mode": "indeterminate", "progress_text": "OCR läuft. Prozentfortschritt ist nicht zuverlässig verfügbar."}))
                            self.events.put(("log", f"OCR gestartet: {total} PDF-Seiten; Sprache {cfg['ocr_language']}."))
                            try:
                                run_ocr(image_pdf, ocr_pdf, cfg["ocr_language"])
                                self.events.put(("log", f"OCR-PDF erfolgreich erstellt: {ocr_pdf}"))
                            except Exception as exc:
                                reason += f" OCR fehlgeschlagen; Bild-PDF bleibt erhalten: {exc}"
                                self.events.put(("log", f"Bild-PDF vorhanden, aber OCR fehlgeschlagen: {exc}"))
                    self.events.put(("stage", {"workflow": "screenshot", "key": "complete",
                        "title": "Export abgeschlossen", "detail": reason, "mode": "determinate",
                        "maximum": 100, "value": 100, "progress_text": "Verarbeitung abgeschlossen"}))
                except Exception as exc:
                    reason += f" PDF-Export fehlgeschlagen: {exc}"
                    self.events.put(("log", f"PDF-Export fehlgeschlagen; PNGs bleiben erhalten: {exc}"))
            elif not test:
                self.events.put(("stage", {"workflow": "screenshot", "key": "complete",
                    "title": "Keine Seiten exportiert", "detail": "Es wurden keine Screenshots gespeichert.",
                    "mode": "determinate", "maximum": 100, "value": 0,
                    "progress_text": "Keine Seiten vorhanden"}))
            self.events.put(("done", {"message": reason, "can_resume": can_resume and not test}))

    # ---------- direct PDF import and PyMuPDF preview ----------
    def choose_pdf(self):
        if self.running:
            return
        filename = filedialog.askopenfilename(parent=self, title="PDF auswählen",
                                              filetypes=[("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")])
        if not filename:
            return
        self.pdf_path = filename
        self.pdf_path_var.set(filename)
        self.pdf_page_index = 0
        self.load_pdf_preview()
        self._update_controls()

    def load_pdf_preview(self):
        try:
            with fitz.open(self.pdf_path) as document:
                if document.needs_pass:
                    raise ValueError("Das PDF ist passwortgeschützt. Bitte zuerst entsperren.")
                self.pdf_page_count = document.page_count
                if not self.pdf_page_count:
                    raise ValueError("Das PDF enthält keine Seiten.")
                self.pdf_page_index = min(max(self.pdf_page_index, 0), self.pdf_page_count - 1)
                page = document.load_page(self.pdf_page_index)
                rect = page.rect
                scale = min(1.5, 1200.0 / max(rect.width, rect.height, 1.0))
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                if pix.n == 1:
                    preview = Image.frombytes("L", (pix.width, pix.height), pix.samples).convert("RGB")
                elif pix.n == 4:
                    preview = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples).convert("RGB")
                else:
                    preview = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                self.pdf_preview_original = preview
                self.pdf_page_label.configure(text=f"Seite {self.pdf_page_index + 1} von {self.pdf_page_count}")
                self.pdf_info_label.configure(text=f"Seitengröße: {rect.width:.1f} × {rect.height:.1f} pt · Ausgabe-DPI werden separat gewählt.")
            self.draw_pdf_preview()
            self._update_controls()
        except Exception as exc:
            self.pdf_page_count = 0
            self.pdf_preview_original = None
            self.pdf_page_label.configure(text="PDF konnte nicht geladen werden")
            self.pdf_info_label.configure(text=str(exc))
            self.draw_pdf_preview()
            self._update_controls()

    def draw_pdf_preview(self, _event=None):
        if not hasattr(self, "pdf_preview_canvas"):
            return
        canvas = self.pdf_preview_canvas
        canvas.delete("all")
        width, height = max(1, canvas.winfo_width()), max(1, canvas.winfo_height())
        if self.pdf_preview_original is None:
            canvas.create_text(width // 2, height // 2, text="PDF-Vorschau erscheint hier",
                               fill="#DCE5F0", font=("Segoe UI", 12), justify="center")
            return
        source = self.pdf_preview_original
        scale = min((width - 24) / source.width, (height - 24) / source.height)
        scale = max(0.05, scale)
        size = (max(1, int(source.width * scale)), max(1, int(source.height * scale)))
        resampling = getattr(Image, "Resampling", Image).LANCZOS
        display = source.resize(size, resampling)
        self.pdf_preview_photo = ImageTk.PhotoImage(display)
        canvas.create_image(width // 2, height // 2, image=self.pdf_preview_photo, anchor="center")

    def pdf_previous(self):
        if self.pdf_page_index > 0:
            self.pdf_page_index -= 1
            self.load_pdf_preview()

    def pdf_next(self):
        if self.pdf_page_index + 1 < self.pdf_page_count:
            self.pdf_page_index += 1
            self.load_pdf_preview()

    def start_pdf_import(self):
        if self.running:
            return
        if not self.pdf_path or not Path(self.pdf_path).is_file():
            messagebox.showwarning("PDF-Import", "Bitte zuerst eine gültige PDF-Datei auswählen.", parent=self)
            return
        try:
            cfg = self._save()
        except (ValueError, tk.TclError):
            messagebox.showerror("Optionen", "Bitte gültige Ausgabeeinstellungen prüfen.", parent=self)
            return
        dpi = DPI_PRESETS.get(self.pdf_resolution_var.get(), 200)
        self.current_workflow = "import"
        self.current_stage = "pdf_render"
        self.running = True
        self.stop_event.clear()
        self._update_controls()
        self._set_stage({"workflow": "import", "key": "pdf_render", "title": "PDF wird gerastert",
                         "detail": f"PyMuPDF rendert mit {dpi} DPI.", "mode": "indeterminate",
                         "progress_text": "PDF wird geöffnet …"})
        self.log(f"PDF-Import gestartet: {self.pdf_path} · {dpi} DPI.")
        threading.Thread(target=self.pdf_import_worker, args=(self.pdf_path, dpi, cfg), daemon=True).start()

    def pdf_import_worker(self, input_path, dpi, cfg):
        reason = "PDF-Import abgeschlossen."
        session = None
        total = pages_rendered = 0
        cancelled = False
        try:
            total = pdf_page_count(input_path)
            session = new_session(cfg["output_dir"])
            timestamp = session.name
            stem = Path(input_path).stem
            safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "imported"
            image_pdf = session / f"{safe_stem}_{timestamp}_{dpi}dpi_image.pdf"
            partial_pdf = session / f"{safe_stem}_{timestamp}_{dpi}dpi_image_partial.pdf"
            self.events.put(("stage", {"workflow": "import", "key": "pdf_render",
                "title": f"PDF-Rasterung · {dpi} DPI", "detail": f"0/{total} Seiten",
                "mode": "determinate", "maximum": total, "value": 0,
                "progress_text": f"0/{total} Seiten"}))
            def report(done, count):
                self.events.put(("progress", {"workflow": "import", "done": done, "total": count}))
            result = render_pdf_to_pdf(input_path, image_pdf, dpi=dpi, progress_callback=report,
                                       stop_event=self.stop_event, partial_output_pdf=partial_pdf)
            pages_rendered = result["pages_rendered"]
            total = result["total_pages"]
            cancelled = result["cancelled"]
            image_pdf = Path(result["output_pdf"]) if result["output_pdf"] else None

            if pages_rendered == 0:
                reason = "Gestoppt vor der ersten fertigen Seite; keine Teildatei erstellt."
                self.events.put(("log", reason))
            elif cancelled:
                reason = f"Rasterung gestoppt nach {pages_rendered}/{total} Seiten. Teil-PDF: {image_pdf}"
                self.events.put(("log", reason))
            else:
                reason = f"Rasterisiertes PDF erstellt: {image_pdf}"
                self.events.put(("log", reason))

            if pages_rendered and cfg["ocr_enabled"]:
                tess = find_tesseract(cfg.get("tesseract_path", ""))
                if not tess:
                    reason += " · Tesseract fehlt; OCR wurde übersprungen."
                    self.events.put(("log", "Tesseract fehlt. Das Bild-/Teil-PDF bleibt erhalten; OCR wurde übersprungen."))
                else:
                    os.environ["PATH"] = str(Path(tess).parent) + os.pathsep + os.environ.get("PATH", "")
                    suffix = "_partial" if cancelled else ""
                    ocr_pdf = session / f"{safe_stem}_{timestamp}_{dpi}dpi_ocr{suffix}.pdf"
                    self.events.put(("stage", {"workflow": "import", "key": "ocr",
                        "title": "OCR für Teil-PDF" if cancelled else "OCR wird ausgeführt",
                        "detail": f"{pages_rendered} Seiten · {cfg['ocr_language']}",
                        "mode": "indeterminate", "progress_text": "OCR läuft"}))
                    self.events.put(("log", f"OCR gestartet: {pages_rendered} Seiten; Sprache {cfg['ocr_language']}."))
                    try:
                        run_ocr(image_pdf, ocr_pdf, cfg["ocr_language"])
                        reason += f" · OCR-PDF: {ocr_pdf}"
                        self.events.put(("log", f"Durchsuchbare OCR-PDF erstellt: {ocr_pdf}"))
                    except Exception as exc:
                        reason += f" · OCR fehlgeschlagen: {exc}"
                        self.events.put(("log", f"Rasterisiertes PDF vorhanden, aber OCR fehlgeschlagen: {exc}"))
        except Exception as exc:
            reason = f"PDF-Import fehlgeschlagen: {exc}"
            self.events.put(("log", reason))
        finally:
            title = "Teil-PDF erstellt" if cancelled and pages_rendered else ("PDF-Import abgeschlossen" if pages_rendered else "Vorgang beendet")
            self.events.put(("stage", {"workflow": "import", "key": "complete", "title": title,
                "detail": f"{pages_rendered}/{total} Seiten", "mode": "determinate",
                "maximum": max(1, total), "value": pages_rendered, "progress_text": reason}))
            self.events.put(("done", {"message": reason, "can_resume": False}))


    # ---------- output folder and Tesseract options ----------
    def choose_output_folder(self):
        initial = self.outdir.get().strip() or str(Path.home())
        folder = filedialog.askdirectory(parent=self, initialdir=initial, title="Ausgabeordner auswählen")
        if folder:
            self.outdir.delete(0, "end")
            self.outdir.insert(0, folder)
            self.refresh_summaries()

    def open_output_folder(self):
        folder = Path(self.outdir.get().strip() or (Path.home() / "Documents" / "PdfSnapOCR"))
        folder.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(folder))
        elif os.sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])

    def choose_tesseract(self):
        filename = filedialog.askopenfilename(parent=self, title="Tesseract-Programmdatei auswählen",
                                              filetypes=[("Tesseract", "tesseract.exe" if os.name == "nt" else "tesseract"),
                                                         ("Alle Dateien", "*.*")])
        if filename:
            self.tesseract_path_var.set(filename)
            self.refresh_tesseract_status()
            self._save_config_safely()

    def refresh_tesseract_status(self):
        path = find_tesseract(self.tesseract_path_var.get())
        if path:
            self.tess_label.configure(text=f"Tesseract gefunden: {path}", style="Success.TLabel")
        else:
            self.tess_label.configure(text="Tesseract nicht gefunden. Für OCR installieren oder den Pfad angeben.", style="Muted.TLabel")

    def install_tesseract(self):
        if self._tesseract_installing:
            return
        self._tesseract_installing = True
        self.tess_install_btn.configure(state="disabled")
        self.tess_label.configure(text="Tesseract wird geprüft bzw. installiert …", style="Muted.TLabel")
        custom = self.tesseract_path_var.get().strip()
        self.log("Tesseract wird geprüft. Eine winget-Installation kann einige Minuten dauern.")
        threading.Thread(target=self._tesseract_worker, args=(custom,), daemon=True).start()

    def _tesseract_worker(self, custom):
        path = find_tesseract(custom)
        installed = False
        if not path:
            installed = install_tesseract()
            path = find_tesseract(custom)
        self.events.put(("tesseract", {"path": path, "installed": installed}))

    def _finish_tesseract(self, result):
        self._tesseract_installing = False
        path = result.get("path")
        if path:
            self.tesseract_path_var.set(path)
            self.tess_label.configure(text=f"Tesseract gefunden: {path}", style="Success.TLabel")
            self.log(f"Tesseract gefunden: {path}")
            self._save_config_safely()
        else:
            self.tess_label.configure(text="Tesseract wurde nicht gefunden bzw. konnte nicht installiert werden.", style="Muted.TLabel")
            self.log("Tesseract nicht gefunden. Installieren Sie es oder geben Sie den Programm-Pfad manuell an.")
        self._update_controls()

    def _save_config_safely(self):
        try:
            self._save()
        except Exception:
            save_config(self.cfg)

    def close(self):
        if self.running:
            if not messagebox.askyesno("Vorgang läuft", "Nach Abschluss des aktuellen Schritts schließen? Eine laufende OCR wird nicht abrupt beendet.", parent=self):
                return
            self._close_when_idle = True
            if self.current_stage in {"capture", "countdown", "pdf_render"}:
                self.stop()
            self._set_status("Schließen nach Abschluss …")
            return
        self._save_config_safely()
        self._closed = True
        self.destroy()
