"""
main.py — Entry point and orchestrator for mouse.ai
Initializes all modules and runs the application.
"""

import sys
import threading
import tkinter as tk
import keyboard

from config import (
    load_config, save_config, prompt_api_key,
    set_auto_start, is_auto_start_enabled
)
from ai_engine import AIEngine
from capture import RegionCapture
from text_selection import TextSelectionMonitor
from popup import ResponsePopup
from tray import TrayManager


class MouseAI:
    """Main application controller."""

    def __init__(self):
        self.config = load_config()
        self.enabled = True
        self.ai_engine = None
        self.root = None
        self.popup = None
        self.text_monitor = None
        self.tray = None
        self._capture_active = False

    def run(self):
        """Start the application."""
        # ── First-run: prompt for API key if missing ──
        if not self.config.get("api_key"):
            api_key = prompt_api_key()
            if not api_key:
                print("[mouse.ai] No API key provided. Exiting.")
                sys.exit(0)
            self.config["api_key"] = api_key
            save_config(self.config)

        # ── Initialize AI engine ──
        self.ai_engine = AIEngine(
            api_key=self.config["api_key"],
            model=self.config.get("model", "gemini-2.5-flash"),
        )

        # ── Setup auto-start ──
        if self.config.get("auto_start", True):
            set_auto_start(True)

        # ── Create hidden tkinter root ──
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the root window
        self.root.title("mouse.ai")

        # ── Initialize popup ──
        self.popup = ResponsePopup(
            self.root,
            auto_dismiss_seconds=self.config.get("auto_dismiss_seconds", 15),
        )

        # ── Initialize text selection monitor (Mode 2) ──
        if self.config.get("text_selection_enabled", True):
            self.text_monitor = TextSelectionMonitor(
                root=self.root,
                on_text_callback=self._on_text_selected,
                icon_linger=self.config.get("icon_linger_seconds", 3),
            )
            self.text_monitor.start()

        # ── Initialize system tray ──
        self.tray = TrayManager(
            on_toggle_callback=self._on_toggle,
            on_settings_callback=self._on_settings,
            on_quit_callback=self._on_quit,
            on_toggle_text_selection=self._on_toggle_text_selection,
        )
        self.tray.start()

        # ── Register global hotkey (Mode 1) ──
        hotkey = self.config.get("hotkey", "alt+a")
        keyboard.add_hotkey(hotkey, self._on_hotkey, suppress=True)
        print(f"[mouse.ai] Started! Hotkey: {hotkey.upper()}")
        print(f"[mouse.ai] Text selection monitor: {'ON' if self.text_monitor else 'OFF'}")
        print(f"[mouse.ai] System tray icon active. Right-click for options.")

        # ── Run tkinter main loop ──
        self._poll_loop()
        self.root.mainloop()

    # ── Mode 1: Region Capture ──────────────────────────────────────

    def _on_hotkey(self):
        """Triggered when the hotkey is pressed."""
        if not self.enabled or self._capture_active:
            return
        # Schedule on the main thread
        self.root.after(0, self._start_capture)

    def _start_capture(self):
        """Start the region capture overlay."""
        self._capture_active = True
        # Temporarily disable text selection monitor during capture
        if self.text_monitor:
            self.text_monitor.set_enabled(False)

        capture = RegionCapture(
            on_capture_callback=self._on_region_captured,
            on_cancel_callback=self._on_capture_cancelled,
        )
        capture.start()

    def _on_region_captured(self, png_bytes: bytes, x: int, y: int):
        """Handle captured region screenshot."""
        self._capture_active = False
        if self.text_monitor and self.config.get("text_selection_enabled", True):
            self.text_monitor.set_enabled(True)

        # Show loading popup
        self.root.after(0, lambda: self.popup.show_loading(x, y))

        # Send to AI in background
        def on_result(result):
            self.root.after(0, lambda: self.popup.update_response(result))

        self.ai_engine.analyze_image_async(png_bytes, on_result)

    def _on_capture_cancelled(self):
        """Handle capture cancellation."""
        self._capture_active = False
        if self.text_monitor and self.config.get("text_selection_enabled", True):
            self.text_monitor.set_enabled(True)

    # ── Mode 2: Text Selection ──────────────────────────────────────

    def _on_text_selected(self, text: str, x: int, y: int):
        """Handle text selection from the floating icon click."""
        # Show loading popup
        self.root.after(0, lambda: self.popup.show_loading(x, y))

        # Send to AI in background
        def on_result(result):
            self.root.after(0, lambda: self.popup.update_response(result))

        self.ai_engine.analyze_text_async(text, on_result)

    # ── Tray callbacks ──────────────────────────────────────────────

    def _on_toggle(self, enabled: bool):
        """Toggle the entire app on/off."""
        self.enabled = enabled
        if self.text_monitor:
            self.text_monitor.set_enabled(enabled and self.config.get("text_selection_enabled", True))

    def _on_toggle_text_selection(self, enabled: bool):
        """Toggle text selection mode specifically."""
        self.config["text_selection_enabled"] = enabled
        save_config(self.config)
        if self.text_monitor:
            self.text_monitor.set_enabled(enabled and self.enabled)

    def _on_settings(self):
        """Open settings dialog."""
        def _show():
            new_key = prompt_api_key(self.config.get("api_key", ""))
            if new_key and new_key != self.config.get("api_key"):
                self.config["api_key"] = new_key
                save_config(self.config)
                # Re-init AI engine with new key
                self.ai_engine = AIEngine(
                    api_key=new_key,
                    model=self.config.get("model", "gemini-2.5-flash"),
                )
        self.root.after(0, _show)

    def _on_quit(self):
        """Clean shutdown."""
        print("[mouse.ai] Shutting down...")
        if self.text_monitor:
            self.text_monitor.stop()
        keyboard.unhook_all()
        self.root.after(0, self.root.destroy)

    def _poll_loop(self):
        """Keep tkinter alive by scheduling periodic no-ops."""
        if self.root and self.root.winfo_exists():
            self.root.after(500, self._poll_loop)


# ── Entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    app = MouseAI()
    app.run()
