"""
tray.py — System tray icon & menu for mouse.ai
Provides enable/disable toggle, settings access, and quit option.
"""

import threading
import pystray
from PIL import Image, ImageDraw, ImageFont


def create_tray_icon_image(active: bool = True) -> Image.Image:
    """Generate a 64x64 tray icon programmatically."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if active:
        # Active: vibrant purple circle with white cursor icon
        draw.ellipse([4, 4, size - 4, size - 4], fill="#7c3aed")
        # Draw a simple cursor/arrow shape
        cursor_points = [
            (20, 14), (20, 46), (28, 38), (36, 50), (42, 46), (34, 34), (44, 34), (20, 14)
        ]
        draw.polygon(cursor_points, fill="#ffffff")
    else:
        # Disabled: gray circle
        draw.ellipse([4, 4, size - 4, size - 4], fill="#585b70")
        cursor_points = [
            (20, 14), (20, 46), (28, 38), (36, 50), (42, 46), (34, 34), (44, 34), (20, 14)
        ]
        draw.polygon(cursor_points, fill="#a6adc8")

    return img


class TrayManager:
    """Manages the system tray icon and context menu."""

    def __init__(
        self,
        on_toggle_callback,
        on_settings_callback,
        on_quit_callback,
        on_toggle_text_selection=None,
    ):
        self.on_toggle = on_toggle_callback
        self.on_settings = on_settings_callback
        self.on_quit = on_quit_callback
        self.on_toggle_text_sel = on_toggle_text_selection
        self.enabled = True
        self.text_sel_enabled = True
        self.icon = None
        self._thread = None

    def start(self):
        """Start the tray icon in a background thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: "✅ Active" if self.enabled else "⬜ Disabled",
                self._on_toggle,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: "✨ Text Selection: ON" if self.text_sel_enabled else "✨ Text Selection: OFF",
                self._on_toggle_text_sel,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚙️ Settings", self._on_settings),
            pystray.MenuItem("ℹ️ About", self._on_about),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Quit", self._on_quit),
        )

        self.icon = pystray.Icon(
            "mouse.ai",
            icon=create_tray_icon_image(True),
            title="mouse.ai — AI Cursor Assistant (Active)",
            menu=menu,
        )
        self.icon.run()

    def _on_toggle(self, icon, item):
        self.enabled = not self.enabled
        icon.icon = create_tray_icon_image(self.enabled)
        icon.title = f"mouse.ai — {'Active' if self.enabled else 'Disabled'}"
        if self.on_toggle:
            self.on_toggle(self.enabled)
        icon.notify(
            f"mouse.ai {'enabled' if self.enabled else 'disabled'}",
            "mouse.ai"
        )

    def _on_toggle_text_sel(self, icon, item):
        self.text_sel_enabled = not self.text_sel_enabled
        if self.on_toggle_text_sel:
            self.on_toggle_text_sel(self.text_sel_enabled)

    def _on_settings(self, icon, item):
        if self.on_settings:
            self.on_settings()

    def _on_about(self, icon, item):
        icon.notify(
            "AI-powered cursor assistant\nAlt+A: Capture region\nSelect text: ✨ icon appears",
            "mouse.ai v1.0"
        )

    def _on_quit(self, icon, item):
        icon.stop()
        if self.on_quit:
            self.on_quit()

    def stop(self):
        if self.icon:
            self.icon.stop()

    def update_icon(self, active: bool):
        if self.icon:
            self.icon.icon = create_tray_icon_image(active)
