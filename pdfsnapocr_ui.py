# -*- coding: utf-8 -*-
"""Tabbed, step-by-step interface for PdfSnapOCR."""
import tkinter as tk
from tkinter import ttk

COLORS = {
    "bg": "#F3F6FA", "surface": "#FFFFFF", "text": "#172033", "muted": "#66758A",
    "line": "#DCE4EE", "blue": "#1769E0", "blue_dark": "#0F56C2", "blue_pale": "#EAF2FF",
    "green": "#16834A", "green_pale": "#E9F7EF", "amber": "#9A6700", "amber_pale": "#FFF5D9",
    "red": "#B42318", "red_pale": "#FFF0EF", "log": "#F9FBFD",
}


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="App.TFrame")
        self.canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = ttk.Frame(self.canvas, style="App.TFrame")
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.content.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window_id, width=e.width))
        self.canvas.bind("<Enter>", lambda _e: self.canvas.bind_all("<MouseWheel>", self._wheel, add="+"))
        self.canvas.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")


class ToolTip:
    """Small hover overlay for explanatory text."""
    def __init__(self, widget, text):
        self.widget, self.text = widget, text
        self.window = None
        self.after_id = None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress-1>", self.hide, add="+")

    def schedule(self, _event=None):
        self.hide()
        try:
            self.after_id = self.widget.after(450, self.show)
        except tk.TclError:
            self.after_id = None

    def show(self):
        self.after_id = None
        try:
            if not self.widget.winfo_exists():
                return
            self.window = tk.Toplevel(self.widget)
            self.window.wm_overrideredirect(True)
            self.window.attributes("-topmost", True)
            tk.Label(self.window, text=self.text, bg="#172033", fg="#FFFFFF",
                     font=("Segoe UI", 9), justify="left", wraplength=300,
                     padx=10, pady=7).pack()
            self.window.update_idletasks()
            x = self.widget.winfo_rootx()
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
            self.window.geometry(f"+{x}+{y}")
        except tk.TclError:
            self.window = None

    def hide(self, _event=None):
        if self.after_id is not None:
            try:
                self.widget.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        if self.window is not None:
            try:
                self.window.destroy()
            except tk.TclError:
                pass
            self.window = None


def _styles(app):
    app.configure(bg=COLORS["bg"])
    style = ttk.Style(app)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(".", font=("Segoe UI", 10), foreground=COLORS["text"])
    style.configure("App.TFrame", background=COLORS["bg"])
    style.configure("Header.TFrame", background=COLORS["surface"])
    style.configure("Footer.TFrame", background=COLORS["surface"])
    style.configure("Card.TFrame", background=COLORS["surface"])
    style.configure("Card.TLabelframe", background=COLORS["surface"], borderwidth=1,
                    relief="solid", bordercolor=COLORS["line"])
    style.configure("Card.TLabelframe.Label", background=COLORS["surface"], foreground=COLORS["muted"],
                    font=("Segoe UI", 9, "bold"), padding=(6, 0))
    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Card.TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("Muted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
    style.configure("Hint.TLabel", background=COLORS["blue_pale"], foreground=COLORS["blue_dark"],
                    padding=(9, 7), wraplength=500)
    style.configure("Warning.TLabel", background=COLORS["amber_pale"], foreground=COLORS["amber"],
                    padding=(9, 7), wraplength=500)
    style.configure("Success.TLabel", background=COLORS["surface"], foreground=COLORS["green"])
    style.configure("Title.TLabel", background=COLORS["surface"], foreground=COLORS["text"],
                    font=("Segoe UI", 20, "bold"))
    style.configure("Subtitle.TLabel", background=COLORS["surface"], foreground=COLORS["muted"],
                    font=("Segoe UI", 9))
    style.configure("CardTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"],
                    font=("Segoe UI", 13, "bold"))
    style.configure("Status.TLabel", background=COLORS["blue_pale"], foreground=COLORS["blue_dark"],
                    padding=(10, 6), font=("Segoe UI", 9, "bold"))
    style.configure("TEntry", padding=(8, 6), fieldbackground=COLORS["surface"])
    style.configure("TCombobox", padding=(7, 6), fieldbackground=COLORS["surface"])
    style.configure("TSpinbox", padding=(7, 5), fieldbackground=COLORS["surface"])
    style.configure("TCheckbutton", background=COLORS["surface"], foreground=COLORS["text"])
    style.map("TCheckbutton", background=[("active", COLORS["surface"])])
    style.configure("TScale", background=COLORS["surface"])
    style.configure("TButton", padding=(10, 7), background="#E9EEF5", foreground=COLORS["text"],
                    borderwidth=0, font=("Segoe UI", 9))
    style.map("TButton", background=[("active", "#DDE5EF"), ("disabled", "#EEF1F5")],
              foreground=[("disabled", "#9AA4B2")])
    style.configure("Primary.TButton", padding=(14, 9), background=COLORS["blue"], foreground="white",
                    font=("Segoe UI", 10, "bold"))
    style.map("Primary.TButton", background=[("active", COLORS["blue_dark"]), ("disabled", "#AABFE3")],
              foreground=[("disabled", "#F6F8FC")])
    style.configure("Danger.TButton", padding=(11, 8), background=COLORS["red_pale"],
                    foreground=COLORS["red"], font=("Segoe UI", 9, "bold"))
    style.map("Danger.TButton", background=[("active", "#FDE1DE"), ("disabled", "#F5F2F2")])
    style.configure("Horizontal.TProgressbar", troughcolor="#E8EDF4", background=COLORS["blue"],
                    bordercolor="#E8EDF4", thickness=9)
    style.configure("Step.TLabel", background="#EFF3F8", foreground=COLORS["muted"],
                    padding=(8, 6), font=("Segoe UI", 9, "bold"))
    style.configure("Step.Active.TLabel", background=COLORS["blue_pale"], foreground=COLORS["blue_dark"],
                    padding=(8, 6), font=("Segoe UI", 9, "bold"))
    style.configure("Step.Done.TLabel", background=COLORS["green_pale"], foreground=COLORS["green"],
                    padding=(8, 6), font=("Segoe UI", 9, "bold"))
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", padding=(17, 10), font=("Segoe UI", 10, "bold"),
                    background="#E7ECF3", foreground=COLORS["muted"])
    style.map("TNotebook.Tab", background=[("selected", COLORS["surface"])],
              foreground=[("selected", COLORS["blue_dark"])])


def _card(parent, title, padding=(13, 11)):
    return ttk.LabelFrame(parent, text=title, style="Card.TLabelframe", padding=padding)


def build_ui(app):
    _styles(app)
    app.title(f"PdfSnapOCR v{app.app_version} · {app.release_date}")
    sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
    width = min(1280, max(760, sw - 70))
    height = min(900, max(620, sh - 75))
    app.geometry(f"{width}x{height}")
    app.minsize(min(980, max(760, sw - 35)), min(650, max(560, sh - 30)))
    # Start maximized so the four screenshot workflow steps and their controls fit at once.
    try:
        app.state("zoomed")
    except tk.TclError:
        pass
    app.columnconfigure(0, weight=1)
    app.rowconfigure(1, weight=1)

    header = ttk.Frame(app, style="Header.TFrame", padding=(20, 13))
    header.grid(row=0, column=0, sticky="ew")
    header.columnconfigure(1, weight=1)
    tk.Label(header, text="PS", bg=COLORS["blue"], fg="white", width=4, height=2,
             font=("Segoe UI", 12, "bold")).grid(row=0, column=0, rowspan=2, padx=(0, 12))
    ttk.Label(header, text="PdfSnapOCR", style="Title.TLabel").grid(row=0, column=1, sticky="sw")
    ttk.Label(header, text="Screenshots aufnehmen oder PDFs direkt mit wählbarer Auflösung verarbeiten",
              style="Subtitle.TLabel").grid(row=1, column=1, sticky="nw", pady=(2, 0))
    status_frame = ttk.Frame(header, style="Header.TFrame")
    status_frame.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))
    ttk.Label(status_frame, text="STATUS", style="Subtitle.TLabel").pack(anchor="e", pady=(0, 4))
    app.status = ttk.Label(status_frame, text="Bereit", style="Status.TLabel", anchor="center",
                           width=28, wraplength=240)
    app.status.pack(anchor="e")

    app.notebook = ttk.Notebook(app)
    app.notebook.grid(row=1, column=0, sticky="nsew", padx=18, pady=(9, 9))
    app.tab_workflow = ttk.Frame(app.notebook, style="App.TFrame", padding=14)
    app.tab_import = ttk.Frame(app.notebook, style="App.TFrame", padding=14)
    app.tab_options = ttk.Frame(app.notebook, style="App.TFrame", padding=14)
    app.notebook.add(app.tab_workflow, text="Screenshot-Aufnahme")
    app.notebook.add(app.tab_import, text="PDF direkt importieren")
    app.notebook.add(app.tab_options, text="Optionen")

    _build_workflow_tab(app)
    _build_import_tab(app)
    _build_options_tab(app)
    app.tooltips = [
        ToolTip(app.region_btn, "Rahmenkörper ziehen zum Verschieben; den Griff unten rechts zum Ändern der Größe verwenden."),
        ToolTip(app.preview_btn, "Öffnet den gesamten Ausschnitt maximiert. Die Vorschau passt ihn automatisch an den Bildschirm an; das PNG bleibt nativ."),
        ToolTip(app.test_btn, "Blättert einmal weiter, um Taste und Wartezeit zu prüfen. Danach ggf. zur Startseite zurückblättern."),
        ToolTip(app.start_btn, "Startet die Aufnahme nach dem Countdown."),
        ToolTip(app.resume_btn, "Nur nach einer gemeldeten Pause verwenden, nachdem Sie den Reader geprüft haben."),
        ToolTip(app.pdf_resolution_combo, "Höhere DPI ergeben mehr Bildpunkte, benötigen aber mehr Zeit und Speicherplatz."),
        ToolTip(app.pdf_notice, "Rasterisieren wandelt vorhandene Vektor-/Textseiten in Bilder um. Aktivierte OCR ergänzt eine durchsuchbare Textebene; die Quelldatei bleibt unberührt."),
    ]

    footer = ttk.Frame(app, style="Footer.TFrame", padding=(18, 9))
    footer.grid(row=2, column=0, sticky="ew")
    footer.columnconfigure(0, weight=1)
    app.footer_status = ttk.Label(footer, text="Bereit", style="Subtitle.TLabel")
    app.footer_status.grid(row=0, column=0, sticky="w", padx=(0, 10))
    app.open_folder_btn = ttk.Button(footer, text="Ausgabeordner öffnen", command=app.open_output_folder)
    app.open_folder_btn.grid(row=0, column=1, padx=(0, 8))
    app.stop_btn = ttk.Button(footer, text="Vorgang stoppen", style="Danger.TButton",
                              command=app.stop, state="disabled")
    app.stop_btn.grid(row=0, column=2)
    app.version_label = ttk.Label(footer, text=f"v{app.app_version} · {app.release_date}", style="Subtitle.TLabel")
    app.version_label.grid(row=0, column=3, sticky="e", padx=(10, 0))


def _build_workflow_tab(app):
    tab = app.tab_workflow
    tab.columnconfigure(0, weight=1)
    tab.rowconfigure(2, weight=1)
    header = ttk.Frame(tab, style="App.TFrame")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 7))
    header.columnconfigure(0, weight=1)
    ttk.Label(header, text="Screenshot-Aufnahme", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
    app.output_summary = ttk.Label(header, text="", style="Muted.TLabel", wraplength=340)
    app.output_summary.grid(row=0, column=1, sticky="e")

    cards = ttk.Frame(tab, style="App.TFrame")
    cards.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    for column in range(4):
        cards.columnconfigure(column, weight=1, uniform="compact_step")
    pad = (9, 7)

    area = _card(cards, "1  BEREICH", padding=pad)
    area.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
    area.columnconfigure(0, weight=1)
    app.region_btn = ttk.Button(area, text="Bereich wählen", style="Primary.TButton", command=app.select_region)
    app.region_btn.grid(row=0, column=0, sticky="ew", pady=(0, 5))
    app.region_label = ttk.Label(area, text="Noch kein Bereich", style="Muted.TLabel", wraplength=215)
    app.region_label.grid(row=1, column=0, sticky="w")
    app.resolution_hint = ttk.Label(area, text="", style="Hint.TLabel", wraplength=215)
    app.resolution_hint.grid(row=2, column=0, sticky="ew", pady=(4, 0))

    preview = _card(cards, "2  VORSCHAU", padding=pad)
    preview.grid(row=0, column=1, sticky="nsew", padx=3)
    preview.columnconfigure(0, weight=1)
    app.preview_btn = ttk.Button(preview, text="Vollbild-Vorschau öffnen", command=app.preview)
    app.preview_btn.grid(row=0, column=0, sticky="ew", pady=(0, 5))
    app.step_preview_status = ttk.Label(preview, text="Ausstehend", style="Muted.TLabel")
    app.step_preview_status.grid(row=1, column=0, sticky="w")

    test = _card(cards, "3  BLÄTTERTEST", padding=pad)
    test.grid(row=0, column=2, sticky="nsew", padx=3)
    test.columnconfigure(0, weight=1)
    app.test_btn = ttk.Button(test, text="Blättertest starten", command=lambda: app.prepare(test=True))
    app.test_btn.grid(row=0, column=0, sticky="ew", pady=(0, 5))
    app.step_test_status = ttk.Label(test, text="Optional", style="Muted.TLabel", wraplength=215)
    app.step_test_status.grid(row=1, column=0, sticky="w")

    start = _card(cards, "4  AUFNAHME", padding=pad)
    start.grid(row=0, column=3, sticky="nsew", padx=(3, 0))
    start.columnconfigure(0, weight=1)
    app.start_btn = ttk.Button(start, text="Aufnahme starten", style="Primary.TButton", command=app.start)
    app.start_btn.grid(row=0, column=0, sticky="ew", pady=(0, 5))
    app.resume_btn = ttk.Button(start, text="Nach Pause fortsetzen", command=app.resume, state="disabled")
    app.resume_btn.grid(row=1, column=0, sticky="ew")
    app.resume_hint = ttk.Label(start, text="Nur nach gemeldeter Pause", style="Muted.TLabel", wraplength=215)
    app.resume_hint.grid(row=2, column=0, sticky="w", pady=(4, 0))

    lower = ttk.Frame(tab, style="App.TFrame")
    lower.grid(row=2, column=0, sticky="nsew")
    lower.columnconfigure(0, weight=2, minsize=300)
    lower.columnconfigure(1, weight=3, minsize=380)
    lower.rowconfigure(0, weight=1)
    progress = _card(lower, "FORTSCHRITT", padding=(11, 9))
    progress.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
    progress.columnconfigure(0, weight=1)
    app.stage_label = ttk.Label(progress, text="Bereit", style="CardTitle.TLabel", wraplength=380)
    app.stage_label.grid(row=0, column=0, sticky="w")
    app.stage_detail = ttk.Label(progress, text="", style="Muted.TLabel", wraplength=380)
    app.stage_detail.grid(row=1, column=0, sticky="w", pady=(2, 6))
    phases = ttk.Frame(progress, style="Card.TFrame")
    phases.grid(row=2, column=0, sticky="ew", pady=(0, 6))
    for column in range(3): phases.columnconfigure(column, weight=1)
    app.phase_widgets = {}
    for column, (key, label_text) in enumerate((("capture", "1 Aufnahme"), ("pdf", "2 Bild-PDF"), ("ocr", "3 OCR"))):
        label = ttk.Label(phases, text=label_text, style="Step.TLabel", anchor="center")
        label.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 3, 0 if column == 2 else 3))
        app.phase_widgets[key] = label
    app.progress = ttk.Progressbar(progress, mode="indeterminate", maximum=100)
    app.progress.grid(row=3, column=0, sticky="ew")
    info = ttk.Frame(progress, style="Card.TFrame")
    info.grid(row=4, column=0, sticky="ew", pady=(4, 0))
    info.columnconfigure(0, weight=1)
    app.progress_label = ttk.Label(info, text="Bereit", style="Muted.TLabel", wraplength=300)
    app.progress_label.grid(row=0, column=0, sticky="w")
    app.timer_label = ttk.Label(info, text="", style="Muted.TLabel")
    app.timer_label.grid(row=0, column=1, sticky="e", padx=(5, 0))

    log_card = _card(lower, "PROTOKOLL", padding=(11, 9))
    log_card.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
    log_card.columnconfigure(0, weight=1)
    log_card.rowconfigure(1, weight=1)
    log_header = ttk.Frame(log_card, style="Card.TFrame")
    log_header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
    log_header.columnconfigure(0, weight=1)
    ttk.Label(log_header, text="Details und Meldungen", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Button(log_header, text="Leeren", command=app.clear_log).grid(row=0, column=1, sticky="e")
    log_body = ttk.Frame(log_card, style="Card.TFrame")
    log_body.grid(row=1, column=0, sticky="nsew")
    log_body.columnconfigure(0, weight=1)
    log_body.rowconfigure(0, weight=1)
    app.log_box = tk.Text(log_body, height=7, wrap="word", bg=COLORS["log"], fg=COLORS["text"],
                          relief="flat", borderwidth=0, padx=8, pady=6, font=("Consolas", 9))
    log_scroll = ttk.Scrollbar(log_body, orient="vertical", command=app.log_box.yview)
    app.log_box.configure(yscrollcommand=log_scroll.set)
    app.log_box.grid(row=0, column=0, sticky="nsew")
    log_scroll.grid(row=0, column=1, sticky="ns")


def _build_import_tab(app):
    tab = app.tab_import
    tab.columnconfigure(0, weight=1)
    tab.rowconfigure(1, weight=1)
    header = ttk.Frame(tab, style="App.TFrame")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    header.columnconfigure(0, weight=1)
    ttk.Label(header, text="PDF direkt importieren", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(header, text="PDF direkt rendern · ohne Screenshot.",
              style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 0))

    body = ttk.Frame(tab, style="App.TFrame")
    body.grid(row=1, column=0, sticky="nsew")
    body.columnconfigure(0, weight=3, minsize=420)
    body.columnconfigure(1, weight=2, minsize=310)
    body.rowconfigure(1, weight=1)
    file_card = _card(body, "QUELL-PDF")
    file_card.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 9))
    file_card.columnconfigure(0, weight=1)
    path_row = ttk.Frame(file_card, style="Card.TFrame")
    path_row.grid(row=0, column=0, sticky="ew")
    path_row.columnconfigure(0, weight=1)
    app.pdf_path_var = tk.StringVar(value="")
    app.pdf_path_entry = ttk.Entry(path_row, textvariable=app.pdf_path_var, state="readonly")
    app.pdf_path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    app.pdf_file_btn = ttk.Button(path_row, text="PDF auswählen …", command=app.choose_pdf)
    app.pdf_file_btn.grid(row=0, column=1, sticky="e")

    viewer = _card(body, "PDF-VORSCHAU")
    viewer.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
    viewer.columnconfigure(0, weight=1)
    viewer.rowconfigure(1, weight=1)
    nav = ttk.Frame(viewer, style="Card.TFrame")
    nav.grid(row=0, column=0, sticky="ew", pady=(0, 7))
    nav.columnconfigure(1, weight=1)
    app.pdf_prev_btn = ttk.Button(nav, text="‹ Vorherige", command=app.pdf_previous)
    app.pdf_prev_btn.grid(row=0, column=0, sticky="w")
    app.pdf_page_label = ttk.Label(nav, text="Keine PDF geladen", style="Muted.TLabel", anchor="center")
    app.pdf_page_label.grid(row=0, column=1, sticky="ew", padx=8)
    app.pdf_next_btn = ttk.Button(nav, text="Nächste ›", command=app.pdf_next)
    app.pdf_next_btn.grid(row=0, column=2, sticky="e")
    app.pdf_preview_canvas = tk.Canvas(viewer, bg="#263449", highlightthickness=0)
    app.pdf_preview_canvas.grid(row=1, column=0, sticky="nsew")
    app.pdf_preview_canvas.bind("<Configure>", app.draw_pdf_preview)
    app.pdf_info_label = ttk.Label(viewer, text="Wählen Sie eine PDF-Datei aus, um die Vorschau zu laden.",
                                   style="Muted.TLabel", wraplength=500)
    app.pdf_info_label.grid(row=2, column=0, sticky="w", pady=(7, 0))

    options = _card(body, "RASTERISIERUNG UND EXPORT")
    options.grid(row=1, column=1, sticky="nsew")
    options.columnconfigure(0, weight=1)
    ttk.Label(options, text="Ausgabeauflösung", style="Card.TLabel").grid(row=0, column=0, sticky="w")
    app.pdf_resolution_var = tk.StringVar(value="Mittel · 200 DPI")
    app.pdf_resolution_combo = ttk.Combobox(
        options, textvariable=app.pdf_resolution_var, state="readonly",
        values=["Niedrig · 96 DPI", "Niedrig · 150 DPI", "Mittel · 200 DPI", "Hoch · 300 DPI", "Sehr hoch · 400 DPI", "Maximal · 600 DPI"],
    )
    app.pdf_resolution_combo.grid(row=1, column=0, sticky="ew", pady=(4, 5))
    ttk.Label(options, text="Mehr DPI = mehr Details, Zeit und Dateigröße.",
              style="Muted.TLabel", wraplength=285).grid(row=2, column=0, sticky="w", pady=(0, 8))
    app.pdf_notice = ttk.Label(
        options,
        text="Raster-PDF · Original bleibt unverändert.",
        style="Warning.TLabel", wraplength=285, justify="left",
    )
    app.pdf_notice.grid(row=3, column=0, sticky="ew", pady=(0, 9))
    app.pdf_ocr_summary = ttk.Label(options, text="OCR-Einstellung wird geladen …", style="Muted.TLabel", wraplength=285)
    app.pdf_ocr_summary.grid(row=4, column=0, sticky="w", pady=(0, 8))
    app.pdf_output_summary = ttk.Label(options, text="", style="Muted.TLabel", wraplength=285)
    app.pdf_output_summary.grid(row=5, column=0, sticky="w", pady=(0, 8))
    app.pdf_run_btn = ttk.Button(options, text="PDF mit gewählter DPI erstellen", style="Primary.TButton",
                                 command=app.start_pdf_import, state="disabled")
    app.pdf_run_btn.grid(row=6, column=0, sticky="ew", pady=(0, 12))
    ttk.Separator(options).grid(row=7, column=0, sticky="ew", pady=(0, 10))
    app.pdf_stage_label = ttk.Label(options, text="Bereit", style="CardTitle.TLabel", wraplength=285)
    app.pdf_stage_label.grid(row=8, column=0, sticky="w")
    app.pdf_progress = ttk.Progressbar(options, mode="determinate", maximum=100)
    app.pdf_progress.grid(row=9, column=0, sticky="ew", pady=(7, 4))
    progress_info = ttk.Frame(options, style="Card.TFrame")
    progress_info.grid(row=10, column=0, sticky="ew")
    progress_info.columnconfigure(0, weight=1)
    app.pdf_progress_label = ttk.Label(progress_info, text="Noch kein Vorgang gestartet", style="Muted.TLabel")
    app.pdf_progress_label.grid(row=0, column=0, sticky="w")
    app.pdf_timer_label = ttk.Label(progress_info, text="", style="Muted.TLabel")
    app.pdf_timer_label.grid(row=1, column=0, sticky="w", pady=(3, 0))


def _build_options_tab(app):
    tab = app.tab_options
    tab.columnconfigure(0, weight=1)
    tab.rowconfigure(0, weight=1)
    scroll = ScrollableFrame(tab)
    scroll.grid(row=0, column=0, sticky="nsew")
    content = scroll.content
    content.columnconfigure(0, weight=1)
    content.columnconfigure(1, weight=1)

    capture = _card(content, "SCREENSHOT-AUFNAHME")
    capture.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=(0, 10))
    capture.columnconfigure(1, weight=1)
    ttk.Label(capture, text="Seitenmodus", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
    app.mode = ttk.Combobox(capture, values=["Einzelseite", "Doppelseite"], state="readonly", width=17)
    app.mode.grid(row=0, column=1, sticky="ew", pady=4)
    ttk.Label(capture, text="Blättertaste", style="Card.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
    app.key = ttk.Combobox(capture, values=["pagedown", "right", "space", "down"], state="readonly", width=17)
    app.key.grid(row=1, column=1, sticky="ew", pady=4)
    ttk.Label(capture, text="Wartezeit nach dem Blättern", style="Card.TLabel").grid(row=2, column=0, columnspan=2, sticky="w", pady=(9, 1))
    app.after_turn = tk.DoubleVar(value=1.0)
    app.after_scale = ttk.Scale(capture, from_=0.2, to=5.0, variable=app.after_turn, orient="horizontal", command=lambda _v: labels(app))
    app.after_scale.grid(row=3, column=0, sticky="ew")
    app.after_label = ttk.Label(capture, text="1.0 s", style="Muted.TLabel")
    app.after_label.grid(row=3, column=1, sticky="e", padx=(8, 0))
    ttk.Label(capture, text="Wartezeit vor Screenshot", style="Card.TLabel").grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 1))
    app.before_capture = tk.DoubleVar(value=0.4)
    app.before_scale = ttk.Scale(capture, from_=0.0, to=3.0, variable=app.before_capture, orient="horizontal", command=lambda _v: labels(app))
    app.before_scale.grid(row=5, column=0, sticky="ew")
    app.before_label = ttk.Label(capture, text="0.4 s", style="Muted.TLabel")
    app.before_label.grid(row=5, column=1, sticky="e", padx=(8, 0))
    ttk.Label(capture, text="Maximale PDF-Seiten", style="Card.TLabel").grid(row=6, column=0, sticky="w", padx=(0, 10), pady=(9, 4))
    app.max_pages = ttk.Spinbox(capture, from_=1, to=5000, width=9)
    app.max_pages.grid(row=6, column=1, sticky="w", pady=(9, 4))
    app.auto_stop = tk.BooleanVar(value=True)
    app.auto_stop_check = ttk.Checkbutton(capture, text="Bei unveränderter Seite pausieren", variable=app.auto_stop)
    app.auto_stop_check.grid(row=7, column=0, columnspan=2, sticky="w", pady=(5, 5))
    ttk.Label(capture, text="Ähnlichkeitsschwelle", style="Card.TLabel").grid(row=8, column=0, columnspan=2, sticky="w", pady=(5, 1))
    app.threshold = tk.DoubleVar(value=0.985)
    app.threshold_scale = ttk.Scale(capture, from_=0.90, to=0.999, variable=app.threshold, orient="horizontal", command=lambda _v: labels(app))
    app.threshold_scale.grid(row=9, column=0, sticky="ew")
    app.threshold_label = ttk.Label(capture, text="98.5 %", style="Muted.TLabel")
    app.threshold_label.grid(row=9, column=1, sticky="e", padx=(8, 0))

    output = _card(content, "AUSGABE UND TEXTERKENNUNG")
    output.grid(row=0, column=1, sticky="nsew", padx=(7, 0), pady=(0, 10))
    output.columnconfigure(0, weight=1)
    ttk.Label(output, text="Ausgabeordner für beide Workflows", style="Card.TLabel").grid(row=0, column=0, sticky="w")
    path_row = ttk.Frame(output, style="Card.TFrame")
    path_row.grid(row=1, column=0, sticky="ew", pady=(4, 10))
    path_row.columnconfigure(0, weight=1)
    app.outdir = ttk.Entry(path_row)
    app.outdir.grid(row=0, column=0, sticky="ew", padx=(0, 7))
    app.outdir_btn = ttk.Button(path_row, text="Durchsuchen …", command=app.choose_output_folder)
    app.outdir_btn.grid(row=0, column=1)
    app.ocr_enabled = tk.BooleanVar(value=True)
    app.ocr_check = ttk.Checkbutton(output, text="Zusätzlich eine durchsuchbare OCR-PDF erstellen", variable=app.ocr_enabled,
                                    command=app.refresh_summaries)
    app.ocr_check.grid(row=2, column=0, sticky="w", pady=(2, 7))
    lang_row = ttk.Frame(output, style="Card.TFrame")
    lang_row.grid(row=3, column=0, sticky="ew", pady=(0, 9))
    lang_row.columnconfigure(1, weight=1)
    ttk.Label(lang_row, text="OCR-Sprache", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 10))
    app.language = ttk.Combobox(lang_row, values=["deu+eng", "deu", "eng", "fra", "ita", "spa"], state="readonly", width=13)
    app.language.grid(row=0, column=1, sticky="ew")
    ttk.Separator(output).grid(row=4, column=0, sticky="ew", pady=(0, 10))
    ttk.Label(output, text="Tesseract-Programmdatei oder Installationsordner", style="Card.TLabel").grid(row=5, column=0, sticky="w")
    tess_path_row = ttk.Frame(output, style="Card.TFrame")
    tess_path_row.grid(row=6, column=0, sticky="ew", pady=(4, 7))
    tess_path_row.columnconfigure(0, weight=1)
    app.tesseract_path_var = tk.StringVar(value="")
    app.tesseract_path_entry = ttk.Entry(tess_path_row, textvariable=app.tesseract_path_var)
    app.tesseract_path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 7))
    app.tesseract_browse_btn = ttk.Button(tess_path_row, text="Datei …", command=app.choose_tesseract)
    app.tesseract_browse_btn.grid(row=0, column=1)
    app.tess_label = ttk.Label(output, text="Tesseract-Status wird geprüft …", style="Muted.TLabel", wraplength=480)
    app.tess_label.grid(row=7, column=0, sticky="w", pady=(2, 7))
    app.tess_install_btn = ttk.Button(output, text="Tesseract prüfen / installieren", command=app.install_tesseract)
    app.tess_install_btn.grid(row=8, column=0, sticky="ew")
    ttk.Label(output, text="Bei einem manuellen Pfad kann eine einzelne `tesseract.exe` oder ein Ordner gewählt werden.",
              style="Muted.TLabel", wraplength=480).grid(row=9, column=0, sticky="w", pady=(8, 0))

    quality = _card(content, "HINWEISE ZUR AUFLÖSUNG")
    quality.grid(row=1, column=0, columnspan=2, sticky="ew")
    ttk.Label(quality,
              text="Screenshot-Aufnahmen behalten die nativen Display-Pixel und werden als PNG gespeichert. Im Doppelseitenmodus teilt sich die Breite auf zwei Seiten. Für die PDF-Importfunktion wählen Sie 150, 200 oder 300 DPI im Import-Tab. Höhere DPI erhöhen Dateigröße und Verarbeitungszeit.",
              style="Muted.TLabel", wraplength=1000, justify="left").grid(row=0, column=0, sticky="ew")

    app.setting_widgets = [app.mode, app.key, app.after_scale, app.before_scale, app.max_pages,
                           app.auto_stop_check, app.threshold_scale, app.outdir, app.ocr_check,
                           app.language, app.tesseract_path_entry, app.tesseract_browse_btn,
                           app.outdir_btn, app.pdf_resolution_combo]


def labels(app):
    app.after_label.configure(text=f"{app.after_turn.get():.1f} s")
    app.before_label.configure(text=f"{app.before_capture.get():.1f} s")
    app.threshold_label.configure(text=f"{app.threshold.get() * 100:.1f} %")
