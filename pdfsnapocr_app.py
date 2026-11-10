# -*- coding: utf-8 -*-
"""Capture with preview, focus countdown, safe pause and positional OCR API."""
import os
import ctypes
import queue
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import mss
import keyboard
import ocrmypdf
from pdfsnapocr_core import load_config, save_config, similar, split_double_page, build_pdf, new_session, find_tesseract
from pdfsnapocr_ui import build_ui, labels, tess_status

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.region = None
        self.running = False
        self.stop_event = threading.Event()
        self.events = queue.Queue()
        self.session = None
        self.captures = []
        self.previous = None
        self.target = None
        self.preview_window = None
        build_ui(self)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        main = self.mode.master
        main.rowconfigure(18, weight=1)
        self.log_box.configure(height=4)
        bar = ttk.Frame(self, padding=8)
        bar.grid(row=1, column=0, sticky="ew")
        ttk.Button(bar, text="Screenshot-Vorschau", command=self.preview).pack(side="left")
        ttk.Button(bar, text="Blaettern testen (5 s)", command=lambda: self.prepare(True)).pack(side="left", padx=8)
        ttk.Button(bar, text="Fortsetzen (5 s)", command=lambda: self.prepare(False, True)).pack(side="left")
        self.status = ttk.Label(bar, text="Vor Aufnahme Vorschau pruefen.")
        self.status.pack(side="left", padx=8)
        for widget, key in [(self.key, 'turn_key'), (self.after_turn, 'delay_after_turn'), (self.before_capture, 'delay_before_capture'), (self.max_pages, 'max_pages'), (self.auto_stop, 'auto_stop'), (self.threshold, 'change_threshold'), (self.ocr_enabled, 'ocr_enabled'), (self.language, 'ocr_language')]:
            widget.set(self.cfg[key])
        self.mode.set('Einzelseite' if self.cfg['page_mode'] == 'single' else 'Doppelseite')
        self.outdir.insert(0, self.cfg['output_dir'])
        labels(self)
        tess_status(self)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(100, self.drain)

    def log(self, text):
        self.log_box.insert('end', f'[{datetime.now():%H:%M:%S}] {text}\n')
        self.log_box.see('end')

    def drain(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'log': self.log(value)
                elif kind == 'done':
                    self.running = False
                    self.start_btn.configure(state='normal')
                    self.stop_btn.configure(state='disabled')
                    self.status.configure(text=value)
                elif kind == 'progress': self.progress.configure(value=value)
        except queue.Empty:
            pass
        self.after(100, self.drain)

    def _save(self):
        self.cfg.update(output_dir=self.outdir.get().strip() or str(Path.home() / 'Documents/PdfSnapOCR'), page_mode='single' if self.mode.get() == 'Einzelseite' else 'double', turn_key=self.key.get(), delay_after_turn=max(.2, float(self.after_turn.get())), delay_before_capture=max(0., float(self.before_capture.get())), max_pages=max(1, int(self.max_pages.get())), auto_stop=bool(self.auto_stop.get()), change_threshold=float(self.threshold.get()), ocr_enabled=bool(self.ocr_enabled.get()), ocr_language=self.language.get())
        save_config(self.cfg)
        return dict(self.cfg)

    def shot(self, region):
        with mss.mss() as sct:
            raw = sct.grab(region)
        return Image.frombytes('RGB', raw.size, raw.rgb)

    def preview(self):
        if self.running or not self.region:
            messagebox.showinfo('Vorschau', 'Zuerst Bereich auswaehlen; laufende Aufnahme vorher stoppen.')
            return
        if self.preview_window and self.preview_window.winfo_exists(): self.preview_window.destroy()
        self.withdraw()
        self.after(500, self.show_preview)

    def show_preview(self):
        try:
            image = self.shot(dict(self.region))
            if self.mode.get() == 'Doppelseite':
                ImageDraw.Draw(image).line((image.width//2, 0, image.width//2, image.height), fill='red', width=3)
            image.thumbnail((900, 600))
            self.deiconify()
            win = self.preview_window = tk.Toplevel(self)
            win.title('Tatsaechlicher Screenshot - rote Linie = Doppelseitenteilung')
            self.preview_image = ImageTk.PhotoImage(image)
            ttk.Label(win, image=self.preview_image).pack()
            ttk.Label(win, text=f"Bereich: {self.region}. Nur vollstaendige PDF-Seiten duerfen sichtbar sein.").pack()
            ttk.Button(win, text='Schliessen und ggf. Bereich neu waehlen', command=win.destroy).pack()
        except Exception as exc:
            self.deiconify()
            messagebox.showerror('Vorschau fehlgeschlagen', str(exc))

    def start(self):
        self.prepare(False)

    def prepare(self, test=False, resume=False):
        if self.running: return
        if not self.region:
            messagebox.showwarning('Aufnahme', 'Bitte zuerst den PDF-Bereich auswaehlen und die Vorschau pruefen.')
            return
        if resume and not self.session:
            messagebox.showinfo('Fortsetzen', 'Es gibt noch keine Sitzung.')
            return
        try: cfg = self._save()
        except ValueError:
            messagebox.showerror('Einstellungen', 'Bitte gueltige Zahlen eingeben.')
            return
        if self.preview_window and self.preview_window.winfo_exists(): self.preview_window.destroy()
        if not test and not resume:
            self.session = new_session(cfg['output_dir'])
            self.captures = []
            self.previous = None
            self.capture_count = 0
            self.session_region = dict(self.region)
            self.session_mode = cfg['page_mode']
        if resume:
            if dict(self.region) != self.session_region or cfg['page_mode'] != self.session_mode:
                messagebox.showerror('Fortsetzen', 'Bereich und Seitenmodus muessen zur bisherigen Sitzung passen. Sonst neue Aufnahme starten.')
                return
        self.running = True
        self.stop_event.clear()
        self.start_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self.log('Bitte jetzt den PDF-Reader aktivieren. In 5 Sekunden wird das aktive Fenster uebernommen.')
        self.countdown(5, test, cfg, dict(self.region))

    def countdown(self, seconds, test, cfg, region):
        if self.stop_event.is_set():
            self.events.put(('done', 'Start abgebrochen.'))
            return
        if seconds:
            self.status.configure(text=f'PDF-Reader aktivieren: {seconds} s')
            self.after(1000, lambda: self.countdown(seconds-1, test, cfg, region))
            return
        if os.name == 'nt':
            self.target = ctypes.windll.user32.GetForegroundWindow()
            own_pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(self.target, ctypes.byref(own_pid))
            if own_pid.value == os.getpid():
                self.log('Kein PDF-Reader ausgewaehlt: PdfSnapOCR hat noch den Fokus.')
                self.events.put(('done', 'Reader aktivieren und erneut starten.'))
                return
        self.status.configure(text='Blaettertest laeuft' if test else 'Aufnahme laeuft')
        threading.Thread(target=self.worker, args=(cfg, region, test), daemon=True).start()

    def stop(self):
        if self.running:
            self.stop_event.set()
            self.log('Stopp angefordert; vorhandene Seiten werden exportiert.')

    def turn(self, cfg):
        if os.name == 'nt' and ctypes.windll.user32.GetForegroundWindow() != self.target:
            raise RuntimeError('Fokus gewechselt. Aufnahme pausiert; PDF-Reader aktivieren und Fortsetzen waehlen.')
        keyboard.press_and_release(cfg['turn_key'])

    def changed(self, old, cfg, region):
        for attempt in range(3):
            if self.stop_event.wait(cfg['delay_after_turn'] + cfg['delay_before_capture']): return None
            image = self.shot(region)
            if not similar(old, image, cfg['change_threshold']): return image
            self.events.put(('log', f'Noch keine Bildaenderung, Pruefung {attempt+1}/3.'))
        return None

    def worker(self, cfg, region, test):
        reason = 'Aufnahme beendet.'
        try:
            if test:
                before = self.shot(region)
                self.turn(cfg)
                changed = self.changed(before, cfg, region)
                self.events.put(('log', 'Blaettertest: Bildaenderung erkannt. Die Seite wurde dabei weitergeblaettert; vor Aufnahme ggf. zurueckblaettern.' if changed is not None else 'Blaettertest: keine Aenderung. Fokus, Taste oder Ladezeit pruefen; alternativ right/space testen.'))
                return
            if self.previous is None:
                if self.stop_event.wait(cfg['delay_before_capture']): return
                image = self.shot(region)
            else:
                image = self.changed(self.previous, cfg, region)
            while image is not None and not self.stop_event.is_set():
                self.capture_count += 1
                path = self.session / f'page_{self.capture_count:04d}.png'
                image.save(path)
                self.captures.extend([path] if cfg['page_mode'] == 'single' else split_double_page(image, self.session, self.capture_count))
                self.previous = image
                self.events.put(('log', f'Screenshot {self.capture_count} gespeichert; {len(self.captures)} PDF-Seiten.'))
                self.events.put(('progress', min(100, len(self.captures)/cfg['max_pages']*100)))
                if len(self.captures) >= cfg['max_pages']: break
                self.turn(cfg)
                image = self.changed(self.previous, cfg, region)
            if image is None and not self.stop_event.is_set():
                reason = 'Pausiert: keine Bildaenderung. Dokumentende ODER Blaettern fehlgeschlagen. Reader pruefen, dann Fortsetzen.'
                self.events.put(('log', reason))
        except Exception as exc:
            reason = f'Pausiert: {exc}'
            self.events.put(('log', reason))
        finally:
            if not test and self.captures:
                try:
                    output = self.session / 'capture_image.pdf'
                    build_pdf(self.captures, output)
                    self.events.put(('log', f'Bild-PDF erstellt: {output}'))
                    if cfg['ocr_enabled']:
                        tess = find_tesseract()
                        if tess: os.environ['PATH'] = str(Path(tess).parent) + os.pathsep + os.environ.get('PATH', '')
                        try:
                            ocrmypdf.ocr(str(output), str(self.session / 'capture_ocr.pdf'), language=cfg['ocr_language'], force_ocr=True, optimize=0, output_type='pdf', progress_bar=False, jobs=1, use_threads=True)
                            self.events.put(('log', 'OCR-PDF erfolgreich erstellt.'))
                        except Exception as exc:
                            self.events.put(('log', f'Bild-PDF vorhanden, aber OCR fehlgeschlagen: {exc}'))
                except Exception as exc:
                    self.events.put(('log', f'PDF-Export fehlgeschlagen; PNGs bleiben erhalten: {exc}'))
            self.events.put(('done', reason))

    def close(self):
        if self.running:
            self.stop_event.set()
            messagebox.showinfo('Aufnahme', 'Stopp angefordert. Bitte Export abwarten und danach schliessen.')
            return
        try: self._save()
        except ValueError: pass
        self.destroy()
