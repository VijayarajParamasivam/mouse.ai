"""
text_selection.py — Text selection detection & floating AI icon (Mode 2)
Pure black themed floating icon with glass effect.
"""

import ctypes
import threading
import time
import tkinter as tk
from pynput import mouse as pynput_mouse
import pyperclip
import keyboard


# ── DWM glass for the icon ──────────────────────────────────────────

def _apply_icon_glass(win):
    """Apply blur + rounded corners to the floating icon."""
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())

        class ACCENTPOLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint),
                ("AnimationId", ctypes.c_int),
            ]

        class WINCOMPATTR(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int),
                ("Data", ctypes.POINTER(ACCENTPOLICY)),
                ("SizeOfData", ctypes.c_size_t),
            ]

        accent = ACCENTPOLICY()
        accent.AccentState = 4
        accent.AccentFlags = 2
        accent.GradientColor = 0xE6080808  # Near-opaque black tint

        data = WINCOMPATTR()
        data.Attribute = 19
        data.Data = ctypes.pointer(accent)
        data.SizeOfData = ctypes.sizeof(accent)
        ctypes.windll.user32.SetWindowCompositionAttribute(
            hwnd, ctypes.pointer(data)
        )

        # Rounded corners
        val = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 33, ctypes.byref(val), ctypes.sizeof(val)
        )
    except Exception:
        pass


# ── Colors ──────────────────────────────────────────────────────────

BG = "#0c0c0c"
HOVER = "#1a1a1a"
ACCENT = "#b48eff"
ACCENT_HOVER = "#d4b5ff"


class TextSelectionMonitor:
    """
    Monitors for text selections globally.
    Shows a floating icon near the cursor when text is selected.
    """

    def __init__(self, root: tk.Tk, on_text_callback, icon_linger: float = 3.0):
        self.root = root
        self.on_text = on_text_callback
        self.icon_linger = icon_linger
        self.enabled = True
        self._listener = None
        self._press_x = 0
        self._press_y = 0
        self._press_time = 0
        self._icon_window = None
        self._fade_timer = None
        self._captured_text = ""
        self._lock = threading.Lock()
        self._is_capturing = False

    def start(self):
        self._listener = pynput_mouse.Listener(on_click=self._on_click)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._hide_icon()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        if not enabled:
            self._hide_icon()

    def _on_click(self, x, y, button, pressed):
        if not self.enabled or button != pynput_mouse.Button.left:
            return
        if pressed:
            self._press_x = x
            self._press_y = y
            self._press_time = time.time()
        else:
            dx = abs(x - self._press_x)
            dy = abs(y - self._press_y)
            dt = time.time() - self._press_time
            if (dx > 30 or dy > 30) and dt > 0.15:
                rx, ry = x, y
                threading.Thread(target=self._check_selection, args=(rx, ry), daemon=True).start()

    def _check_selection(self, x: int, y: int):
        with self._lock:
            if self._is_capturing:
                return
            self._is_capturing = True
        try:
            try:
                old = pyperclip.paste()
            except Exception:
                old = ""

            time.sleep(0.1)
            keyboard.press_and_release("ctrl+c")
            time.sleep(0.15)

            try:
                new = pyperclip.paste()
            except Exception:
                new = ""

            if new and new != old and len(new.strip()) > 0:
                self._captured_text = new.strip()
                self.root.after(0, lambda: self._show_icon(x, y))
            else:
                try:
                    if old:
                        pyperclip.copy(old)
                except Exception:
                    pass
        finally:
            with self._lock:
                self._is_capturing = False

    def _show_icon(self, x: int, y: int):
        self._hide_icon()

        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.0)
        win.configure(bg=BG)

        iw, ih = 38, 38
        sw = win.winfo_screenwidth()
        ix = x + 12
        iy = y - 42
        if ix + iw > sw - 8:
            ix = x - iw - 12
        if iy < 8:
            iy = y + 16

        win.geometry(f"{iw}x{ih}+{ix}+{iy}")
        win.after(10, lambda: _apply_icon_glass(win))

        # Border frame
        border = tk.Frame(win, bg="#2a2a2a", padx=1, pady=1)
        border.pack(fill="both", expand=True)
        inner = tk.Frame(border, bg=BG)
        inner.pack(fill="both", expand=True)

        btn = tk.Label(
            inner, text="✦", font=("Segoe UI", 15, "bold"),
            bg=BG, fg=ACCENT, cursor="hand2",
        )
        btn.pack(expand=True, fill="both")

        def enter(e):
            btn.configure(bg=HOVER, fg=ACCENT_HOVER)
            inner.configure(bg=HOVER)
        def leave(e):
            btn.configure(bg=BG, fg=ACCENT)
            inner.configure(bg=BG)
        btn.bind("<Enter>", enter)
        btn.bind("<Leave>", leave)

        def click(e):
            t = self._captured_text
            self._hide_icon()
            if t and self.on_text:
                self.on_text(t, x, y)
        btn.bind("<Button-1>", click)

        self._icon_window = win
        self._fade_in(win, 0)
        self._fade_timer = self.root.after(int(self.icon_linger * 1000), self._fade_out_hide)

    def _fade_in(self, w, s):
        if not w or not w.winfo_exists():
            return
        a = min(0.96, s * 0.12)
        try:
            w.attributes("-alpha", a)
        except tk.TclError:
            return
        if a < 0.94:
            self.root.after(18, lambda: self._fade_in(w, s + 1))

    def _fade_out_hide(self):
        if self._icon_window and self._icon_window.winfo_exists():
            self._fade_out(self._icon_window, 0.96)

    def _fade_out(self, w, a):
        if not w or not w.winfo_exists():
            return
        a -= 0.12
        if a <= 0:
            self._hide_icon()
            return
        try:
            w.attributes("-alpha", a)
        except tk.TclError:
            return
        self.root.after(18, lambda: self._fade_out(w, a))

    def _hide_icon(self):
        if self._fade_timer:
            try:
                self.root.after_cancel(self._fade_timer)
            except Exception:
                pass
            self._fade_timer = None
        if self._icon_window:
            try:
                self._icon_window.destroy()
            except Exception:
                pass
            self._icon_window = None
