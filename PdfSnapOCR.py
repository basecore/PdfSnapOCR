# -*- coding: utf-8 -*-
"""PdfSnapOCR start entry point with per-monitor DPI awareness on Windows."""
import os

if os.name == "nt":
    import ctypes
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

from pdfsnapocr_app import App

if __name__ == "__main__":
    App().mainloop()
