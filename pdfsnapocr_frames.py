# -*- coding: utf-8 -*-
"""Movable/resizable capture frame with absolute virtual-desktop coordinates on Windows."""
import ctypes
import os
import tkinter as tk
from ctypes import wintypes


class FrameSelector(tk.Toplevel):
    def __init__(self, parent, page_mode="single"):
        super().__init__(parent)
        self.result = None
        self._drag_offset = None
        self._resize_start = None
        self._x = self._y = 0
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.38)
        except tk.TclError:
            pass
        self.configure(bg="#0B1220")
        sw, sh = int(parent.winfo_screenwidth()), int(parent.winfo_screenheight())
        width, height = min(1050, int(sw * 0.68)), min(720, int(sh * 0.74))
        x, y = max(0, (sw - width) // 2), max(0, (sh - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.update_idletasks()
        self._x, self._y = int(self.winfo_rootx()), int(self.winfo_rooty())
        self.canvas = tk.Canvas(self, bg="#0B1220", highlightthickness=3,
                                highlightbackground="#1769E0", cursor="fleur")
        self.canvas.pack(fill="both", expand=True)
        title = "DOPPELSEITENBEREICH" if page_mode == "double" else "EINZELSEITENBEREICH"
        instruction = (
            "Rahmen über beide sichtbaren Seiten legen. Die Aufnahme wird mittig geteilt."
            if page_mode == "double" else
            "Rahmen über die sichtbare PDF-Seite legen. Menüs und Taskleiste möglichst ausschließen."
        )
        self.header = tk.Frame(self.canvas, bg="#FFFFFF", padx=14, pady=8)
        self.header.place(relx=0.5, rely=0.025, anchor="n")
        self.title_label = tk.Label(self.header, text=title, bg="#FFFFFF", fg="#172033",
                                    font=("Segoe UI", 10, "bold"))
        self.title_label.pack()
        self.instruction_label = tk.Label(self.header, text=instruction, bg="#FFFFFF", fg="#526176",
                                          font=("Segoe UI", 9), wraplength=620, justify="center")
        self.instruction_label.pack(pady=(3, 0))
        self.size_label = tk.Label(self.canvas, text="", bg="#1769E0", fg="#FFFFFF",
                                   font=("Segoe UI", 10, "bold"), padx=12, pady=6)
        self.size_label.place(relx=0.5, rely=0.85, anchor="center")
        self.controls = tk.Frame(self.canvas, bg="#FFFFFF", padx=8, pady=7)
        self.controls.place(relx=0.5, rely=0.97, anchor="s")
        self.cancel_button = tk.Button(self.controls, text="Abbrechen", command=self.destroy,
            bg="#EEF2F7", fg="#172033", activebackground="#E1E7EF", relief="flat", borderwidth=0,
            font=("Segoe UI", 9), padx=14, pady=7, cursor="hand2")
        self.cancel_button.pack(side="left", padx=(0, 7))
        self.confirm_button = tk.Button(self.controls, text="Bereich übernehmen", command=self.confirm,
            bg="#1769E0", fg="#FFFFFF", activebackground="#0F56C2", relief="flat", borderwidth=0,
            font=("Segoe UI", 9, "bold"), padx=15, pady=7, cursor="hand2")
        self.confirm_button.pack(side="left")
        self.handle = tk.Label(self.canvas, text="◢", bg="#1769E0", fg="#FFFFFF",
                               font=("Segoe UI", 14, "bold"), padx=5, pady=3, cursor="size_nw_se")
        self.handle.place(relx=1.0, rely=1.0, anchor="se", x=-4, y=-4)
        self.bind("<ButtonPress-1>", self.press, add="+")
        self.bind("<B1-Motion>", self.drag, add="+")
        for widget in (self.canvas, self.header, self.title_label, self.instruction_label, self.size_label):
            widget.bind("<ButtonPress-1>", self.press, add="+")
            widget.bind("<B1-Motion>", self.drag, add="+")
        self.handle.bind("<ButtonPress-1>", self.resize_press, add="+")
        self.handle.bind("<B1-Motion>", self.resize_drag, add="+")
        self.bind("<Escape>", lambda _event: self.destroy())
        self.after(100, self.update_size)

    def _place_window(self, x, y, width, height):
        self._x, self._y = int(x), int(y)
        width, height = int(width), int(height)
        if os.name == "nt":
            try:
                user32 = ctypes.windll.user32
                client_hwnd = wintypes.HWND(int(self.winfo_id()))
                root_hwnd = user32.GetAncestor(client_hwnd, 2)
                hwnd = wintypes.HWND(root_hwnd or client_hwnd.value)
                set_window_pos = user32.SetWindowPos
                set_window_pos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                           ctypes.c_int, ctypes.c_int, wintypes.UINT]
                set_window_pos.restype = wintypes.BOOL
                flags = 0x0010 | 0x0040
                if set_window_pos(hwnd, wintypes.HWND(-1), self._x, self._y, width, height, flags):
                    return
            except Exception:
                pass
        self.geometry(f"{width}x{height}{self._x:+d}{self._y:+d}")

    def press(self, event):
        self._drag_offset = None
        if event.widget in (self.handle, self.cancel_button, self.confirm_button):
            return
        self._drag_offset = (event.x_root - self._x, event.y_root - self._y)

    def drag(self, event):
        if self._drag_offset is not None:
            x = event.x_root - self._drag_offset[0]
            y = event.y_root - self._drag_offset[1]
            self._place_window(x, y, self.winfo_width(), self.winfo_height())

    def resize_press(self, event):
        self._drag_offset = None
        self._resize_start = (event.x_root, event.y_root, self.winfo_width(), self.winfo_height(), self._x, self._y)

    def resize_drag(self, event):
        if not self._resize_start:
            return
        sx, sy, width, height, x, y = self._resize_start
        self._place_window(x, y, max(300, width + event.x_root - sx), max(250, height + event.y_root - sy))

    def update_size(self):
        if self.winfo_exists():
            self.size_label.configure(text=f"{self.winfo_width()} × {self.winfo_height()} Pixel")
            self.after(120, self.update_size)

    def confirm(self):
        if self.winfo_width() < 100 or self.winfo_height() < 100:
            return
        self.result = {"left": int(self._x), "top": int(self._y),
                       "width": int(self.winfo_width()), "height": int(self.winfo_height())}
        self.destroy()
