# -*- coding: utf-8 -*-
"""Manually movable and resizable PDF capture frame for PdfSnapOCR."""

import tkinter as tk

class FrameSelector(tk.Toplevel):
    def __init__(self, parent, page_mode="single"):
        super().__init__(parent)
        self.result = None
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.28)
        self.configure(bg="#0b1220")

        sw, sh = parent.winfo_screenwidth(), parent.winfo_screenheight()
        w, h = min(1000, int(sw * .65)), min(700, int(sh * .7))
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self.canvas = tk.Canvas(self, bg="#0b1220", highlightthickness=3,
                                highlightbackground="#2563eb", cursor="fleur")
        self.canvas.pack(fill="both", expand=True)

        text = ("DOPPELSEITENMODUS\n\nLege den Rahmen über beide nebeneinander liegenden PDF-Seiten.\n"
                "Der Bereich wird später automatisch geteilt." if page_mode == "double"
                else "EINZELSEITENMODUS\n\nLege den Rahmen genau über die sichtbare PDF-Seite.\n"
                "Menüs, Taskleiste und Scrollbalken möglichst ausschließen.")

        tk.Label(self.canvas, text=text, bg="white", fg="#111827", font=("Segoe UI", 11, "bold"),
                 padx=18, pady=12, justify="center").place(relx=.5, rely=.06, anchor="center")

        self.size_label = tk.Label(self.canvas, bg="#2563eb", fg="white",
                                   font=("Segoe UI", 10, "bold"), padx=12, pady=6)
        self.size_label.place(relx=.5, rely=.94, anchor="center")

        tk.Button(self.canvas, text="✔ Bereich bestätigen", command=self.confirm,
                  bg="#2563eb", fg="white", activebackground="#1d4ed8", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=16, pady=8, cursor="hand2"
                  ).place(relx=.5, rely=.84, anchor="center")

        tk.Button(self.canvas, text="✖ Abbrechen", command=self.destroy,
                  bg="#e5e7eb", fg="#111827", relief="flat", font=("Segoe UI", 10),
                  padx=14, pady=8, cursor="hand2").place(relx=.5, rely=.94, anchor="center")

        self.handle = tk.Label(self.canvas, text="◢", bg="#2563eb", fg="white",
                               font=("Segoe UI", 14, "bold"), padx=8, pady=4, cursor="size_nw_se")
        self.handle.place(relx=1, rely=1, anchor="se", x=-8, y=-8)

        self.drag_start = self.resize_start = None
        self.canvas.bind("<ButtonPress-1>", self.press)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.bind("<Escape>", lambda e: self.destroy())
        self.handle.bind("<ButtonPress-1>", self.resize_press)
        self.handle.bind("<B1-Motion>", self.resize_drag)
        self.after(80, self.update_size)

    def press(self, event):
        if event.widget is self.handle: return
        self.drag_start = (event.x_root - self.winfo_x(), event.y_root - self.winfo_y())

    def drag(self, event):
        if self.drag_start:
            self.geometry(f"+{event.x_root - self.drag_start[0]}+{event.y_root - self.drag_start[1]}")

    def resize_press(self, event):
        self.resize_start = (event.x_root, event.y_root, self.winfo_width(), self.winfo_height())

    def resize_drag(self, event):
        if not self.resize_start: return
        x, y, w, h = self.resize_start
        self.geometry(f"{max(300, w + event.x_root - x)}x{max(250, h + event.y_root - y)}")

    def update_size(self):
        if not self.winfo_exists(): return
        self.size_label.config(text=f"{self.winfo_width()} × {self.winfo_height()} Pixel")
        self.after(100, self.update_size)

    def confirm(self):
        if self.winfo_width() < 100 or self.winfo_height() < 100: return
        self.result = {"left": int(self.winfo_x()), "top": int(self.winfo_y()),
                       "width": int(self.winfo_width()), "height": int(self.winfo_height())}
        self.destroy()
