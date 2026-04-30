"""
capture.py — Screen region selection & capture (Mode 1) for mouse.ai
Creates a fullscreen semi-transparent overlay for drag-to-select region capture.
"""

import io
import tkinter as tk
import mss
from PIL import Image


class RegionCapture:
    """
    Fullscreen overlay that lets the user drag-select a screen region.
    On release, captures that region as PNG bytes.
    """

    def __init__(self, on_capture_callback, on_cancel_callback=None):
        """
        Args:
            on_capture_callback: Called with (png_bytes, x, y) where x,y is cursor pos.
            on_cancel_callback: Called when user presses Escape.
        """
        self.on_capture = on_capture_callback
        self.on_cancel = on_cancel_callback
        self.start_x = 0
        self.start_y = 0
        self.rect_id = None
        self.root = None

    def start(self):
        """Show the overlay and begin selection mode."""
        self.root = tk.Toplevel()
        root = self.root

        # Get full virtual screen bounds (multi-monitor)
        root.update_idletasks()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()

        # Fullscreen borderless window
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.3)
        root.geometry(f"{screen_w}x{screen_h}+0+0")
        root.configure(bg="#000000")

        # Canvas for drawing selection rectangle
        self.canvas = tk.Canvas(
            root,
            width=screen_w,
            height=screen_h,
            bg="#000000",
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True)

        # Instruction text
        self.canvas.create_text(
            screen_w // 2, 40,
            text="Click and drag to select a region  •  Press Esc to cancel",
            font=("Segoe UI", 13),
            fill="#ffffff",
        )

        # Bind events
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        root.bind("<Escape>", self._on_escape)

        root.focus_force()

    def _on_press(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        if self.rect_id:
            self.canvas.delete(self.rect_id)

    def _on_drag(self, event):
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        # Draw selection rectangle
        x1 = min(self.start_x, event.x_root)
        y1 = min(self.start_y, event.y_root)
        x2 = max(self.start_x, event.x_root)
        y2 = max(self.start_y, event.y_root)
        self.rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#a6e3a1",
            width=2,
            dash=(6, 4),
        )

    def _on_release(self, event):
        x1 = min(self.start_x, event.x_root)
        y1 = min(self.start_y, event.y_root)
        x2 = max(self.start_x, event.x_root)
        y2 = max(self.start_y, event.y_root)

        # Minimum selection size
        if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
            self._cleanup()
            if self.on_cancel:
                self.on_cancel()
            return

        # Hide overlay before capture (so it's not in the screenshot)
        self._cleanup()

        # Small delay to let the overlay disappear
        self.root = None
        import time
        time.sleep(0.05)

        # Capture the region
        try:
            png_bytes = self._capture_region(x1, y1, x2, y2)
            cursor_x, cursor_y = event.x_root, event.y_root
            self.on_capture(png_bytes, cursor_x, cursor_y)
        except Exception as e:
            print(f"[capture] Error capturing region: {e}")

    def _on_escape(self, event):
        self._cleanup()
        if self.on_cancel:
            self.on_cancel()

    def _cleanup(self):
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass

    @staticmethod
    def _capture_region(x1: int, y1: int, x2: int, y2: int) -> bytes:
        """Capture a screen region and return PNG bytes."""
        region = {
            "left": x1,
            "top": y1,
            "width": x2 - x1,
            "height": y2 - y1,
        }
        with mss.mss() as sct:
            screenshot = sct.grab(region)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
