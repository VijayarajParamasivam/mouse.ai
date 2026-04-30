"""
config.py — Configuration management for mouse.ai
Handles loading/saving config, first-run API key dialog, and auto-start registry.
"""

import json
import os
import sys
import tkinter as tk
from tkinter import messagebox
import winreg

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "api_key": "",
    "hotkey": "alt+a",
    "auto_dismiss_seconds": 15,
    "model": "gemini-2.5-flash",
    "text_selection_enabled": True,
    "region_capture_enabled": True,
    "auto_start": True,
    "icon_linger_seconds": 3,
}

APP_NAME = "mouse.ai"
APP_EXE_PATH = os.path.abspath(sys.argv[0])


def load_config() -> dict:
    """Load config from disk, merging with defaults for missing keys."""
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config.update(saved)
        except (json.JSONDecodeError, IOError):
            pass
    return config


def save_config(config: dict):
    """Persist config to disk."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        print(f"[config] Failed to save config: {e}")


def _apply_dialog_glass(dialog):
    """Apply DWM glass effect to the dialog."""
    try:
        import ctypes
        dialog.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(dialog.winfo_id())

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
        accent.GradientColor = 0xE6080808  # Near-opaque black

        data = WINCOMPATTR()
        data.Attribute = 19
        data.Data = ctypes.pointer(accent)
        data.SizeOfData = ctypes.sizeof(accent)
        ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.pointer(data))

        val = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(val), ctypes.sizeof(val))

        dark = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))
    except Exception:
        pass


def prompt_api_key(existing_key: str = "") -> str:
    """
    Show a black glass dialog to enter/update the Gemini API key.
    Returns the key string, or empty string if cancelled.
    """
    BG = "#0c0c0c"
    SURFACE = "#141414"
    BORDER = "#2a2a2a"
    TEXT = "#f0f0f0"
    MUTED = "#999999"
    ACCENT = "#b48eff"
    BTN_BG = "#1a1a1a"

    result = {"key": existing_key}

    dialog = tk.Tk()
    dialog.title("mouse.ai")
    dialog.configure(bg=BG)
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)

    w, h = 460, 300
    sx = dialog.winfo_screenwidth() // 2 - w // 2
    sy = dialog.winfo_screenheight() // 2 - h // 2
    dialog.geometry(f"{w}x{h}+{sx}+{sy}")

    dialog.after(10, lambda: _apply_dialog_glass(dialog))

    # ── Icon + Title ──
    tk.Label(
        dialog, text="✦", font=("Segoe UI", 28, "bold"),
        fg=ACCENT, bg=BG,
    ).pack(pady=(28, 0))

    tk.Label(
        dialog, text="mouse.ai", font=("Segoe UI", 15, "bold"),
        fg=TEXT, bg=BG,
    ).pack(pady=(2, 0))

    tk.Label(
        dialog, text="Enter your Gemini API key to get started",
        font=("Segoe UI", 10), fg=MUTED, bg=BG,
    ).pack(pady=(2, 14))

    # ── API key entry ──
    entry_outer = tk.Frame(dialog, bg=BORDER, padx=1, pady=1)
    entry_outer.pack(padx=40, fill="x")

    entry_inner = tk.Frame(entry_outer, bg=SURFACE, padx=12, pady=10)
    entry_inner.pack(fill="x")

    entry = tk.Entry(
        entry_inner,
        font=("Cascadia Code", 11),
        fg=TEXT, bg=SURFACE,
        insertbackground=ACCENT,
        relief="flat", show="•",
        highlightthickness=0,
    )
    entry.pack(fill="x")
    if existing_key:
        entry.insert(0, existing_key)

    # ── Show/hide toggle ──
    show_var = tk.BooleanVar(value=False)

    def toggle_show():
        entry.config(show="" if show_var.get() else "•")

    tk.Checkbutton(
        dialog, text="Show key", variable=show_var, command=toggle_show,
        font=("Segoe UI", 9), fg=MUTED, bg=BG,
        selectcolor=SURFACE, activebackground=BG, activeforeground=TEXT,
    ).pack(anchor="w", padx=42, pady=(4, 0))

    # ── Buttons ──
    btn_frame = tk.Frame(dialog, bg=BG)
    btn_frame.pack(pady=(14, 0))

    def on_save():
        key = entry.get().strip()
        if not key:
            messagebox.showwarning("Missing Key", "Please enter a valid API key.",
                                   parent=dialog)
            return
        result["key"] = key
        dialog.destroy()

    def on_cancel():
        dialog.destroy()

    # Save button
    save_outer = tk.Frame(btn_frame, bg=ACCENT, padx=1, pady=1)
    save_outer.pack(side="left", padx=6)
    save_btn = tk.Label(
        save_outer, text="  Save Key  ", font=("Segoe UI", 11, "bold"),
        fg="#0a0a0a", bg=ACCENT, cursor="hand2", padx=14, pady=5,
    )
    save_btn.pack()
    save_btn.bind("<Button-1>", lambda e: on_save())
    save_btn.bind("<Enter>", lambda e: save_btn.configure(bg="#d4b5ff"))
    save_btn.bind("<Leave>", lambda e: save_btn.configure(bg=ACCENT))

    # Cancel button
    cancel_outer = tk.Frame(btn_frame, bg=BORDER, padx=1, pady=1)
    cancel_outer.pack(side="left", padx=6)
    cancel_btn = tk.Label(
        cancel_outer, text="  Cancel  ", font=("Segoe UI", 11),
        fg=MUTED, bg=BTN_BG, cursor="hand2", padx=14, pady=5,
    )
    cancel_btn.pack()
    cancel_btn.bind("<Button-1>", lambda e: on_cancel())
    cancel_btn.bind("<Enter>", lambda e: cancel_btn.configure(fg=TEXT, bg="#252525"))
    cancel_btn.bind("<Leave>", lambda e: cancel_btn.configure(fg=MUTED, bg=BTN_BG))

    # ── Hint ──
    tk.Label(
        dialog, text="Get your key at aistudio.google.com",
        font=("Segoe UI", 9), fg="#555555", bg=BG,
    ).pack(side="bottom", pady=10)

    entry.focus_set()
    dialog.bind("<Return>", lambda e: on_save())
    dialog.bind("<Escape>", lambda e: on_cancel())
    dialog.mainloop()

    return result["key"]


# ── Windows Auto-Start ──────────────────────────────────────────────

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def set_auto_start(enable: bool = True):
    """Add or remove mouse.ai from Windows startup registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH,
                             0, winreg.KEY_SET_VALUE)
        if enable:
            # Use pythonw from venv to avoid console window
            venv_pythonw = os.path.join(CONFIG_DIR, "venv", "Scripts", "pythonw.exe")
            if os.path.exists(venv_pythonw):
                exe = venv_pythonw
            else:
                exe = sys.executable
                if exe.endswith("python.exe"):
                    exe = exe.replace("python.exe", "pythonw.exe")
            main_py = os.path.join(CONFIG_DIR, "main.py")
            cmd = f'"{exe}" "{main_py}"'
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except OSError as e:
        print(f"[config] Auto-start registry error: {e}")


def is_auto_start_enabled() -> bool:
    """Check if mouse.ai is in the Windows startup registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH,
                             0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False
