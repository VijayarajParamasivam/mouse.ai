"""
popup.py — Pure black glass AI response popup for mouse.ai
True dark theme with high-contrast readable text, auto-sizing, and DWM effects.
"""

import ctypes
import ctypes.wintypes
import tkinter as tk
import tkinter.font as tkfont
import textwrap


# ── Windows DWM APIs ────────────────────────────────────────────────

class _ACCENTPOLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int),
    ]

class _WINCOMPATTR(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.POINTER(_ACCENTPOLICY)),
        ("SizeOfData", ctypes.c_size_t),
    ]


def _apply_glass_effect(toplevel_win):
    """Apply acrylic blur + rounded corners + dark mode."""
    try:
        toplevel_win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(toplevel_win.winfo_id())

        # Acrylic blur-behind
        accent = _ACCENTPOLICY()
        accent.AccentState = 4  # ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.AccentFlags = 2
        accent.GradientColor = 0xE6080808  # ABGR: near-opaque black

        data = _WINCOMPATTR()
        data.Attribute = 19  # WCA_ACCENT_POLICY
        data.Data = ctypes.pointer(accent)
        data.SizeOfData = ctypes.sizeof(accent)
        ctypes.windll.user32.SetWindowCompositionAttribute(
            hwnd, ctypes.pointer(data)
        )

        # Rounded corners (Win 11)
        val = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 33, ctypes.byref(val), ctypes.sizeof(val)
        )

        # Dark mode
        dark = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark)
        )
    except Exception:
        pass


# ── Color Palette — True Black ─────────────────────────────────────

C = {
    "bg":          "#0c0c0c",   # Near-black background
    "surface":     "#141414",   # Card/surface
    "hover":       "#1c1c1c",   # Hover state
    "border":      "#2a2a2a",   # Subtle border
    "glow":        "#3a3a3a",   # Accent border
    "text":        "#f0f0f0",   # Primary text — bright white
    "text_sec":    "#999999",   # Secondary text
    "accent":      "#b48eff",   # Soft purple accent
    "success":     "#5af0b0",   # Copy confirmation green
    "close_hover": "#ff5555",   # Close button red
    "sep":         "#222222",   # Separator
}


def _font(size=11, weight="normal"):
    """Get best available modern font."""
    for family in ("Segoe UI Variable", "Segoe UI", "Calibri"):
        try:
            f = tkfont.Font(family=family, size=size, weight=weight)
            if family.lower() in f.actual()["family"].lower():
                return (family, size, weight)
        except Exception:
            continue
    return ("Segoe UI", size, weight)


# ── Text measurement for auto-sizing ───────────────────────────────

def _measure_text(text: str, font_tuple: tuple, max_width_px: int) -> tuple:
    """Calculate required dimensions. Returns (width, height, line_count)."""
    temp = tk.Toplevel()
    temp.withdraw()
    f = tkfont.Font(temp, font=font_tuple)
    line_h = f.metrics("linespace") + 4  # Extra spacing for readability

    raw_lines = text.split("\n")
    total_lines = 0
    max_w = 0

    for raw in raw_lines:
        if not raw.strip():
            total_lines += 1
            continue
        w = f.measure(raw)
        if w <= max_width_px:
            total_lines += 1
            max_w = max(max_w, w)
        else:
            cpl = max(20, int(len(raw) * max_width_px / w))
            subs = textwrap.wrap(raw, width=cpl)
            total_lines += len(subs)
            for s in subs:
                max_w = max(max_w, f.measure(s))

    temp.destroy()
    return min(max_w + 16, max_width_px), total_lines * line_h, total_lines


# ── Popup ───────────────────────────────────────────────────────────

class ResponsePopup:
    """
    Pure black, high-contrast popup for AI responses.
    Auto-sizes to content. Only scrolls when text is very long.
    """

    MIN_W = 260
    MAX_W = 540
    MAX_H_RATIO = 0.55  # Max 55% of screen height
    PAD = 18

    def __init__(self, root: tk.Tk, auto_dismiss_seconds: int = 15):
        self.root = root
        self.auto_dismiss = auto_dismiss_seconds
        self._popup = None
        self._dismiss_timer = None
        self._pos = (200, 200)

    def show_loading(self, x: int, y: int):
        self._pos = (x, y)
        self._destroy_popup()
        self._build_loading(x, y)

    def show_response(self, text: str, x: int, y: int):
        self._destroy_popup()
        self._build_response(text, x, y)

    def update_response(self, text: str):
        self._destroy_popup()
        self._build_response(text, self._pos[0], self._pos[1])

    # ── Loading ─────────────────────────────────────────────────────

    def _build_loading(self, x, y):
        p = tk.Toplevel(self.root)
        p.overrideredirect(True)
        p.attributes("-topmost", True)
        p.attributes("-alpha", 0.0)
        p.configure(bg=C["bg"])

        w, h = 200, 68
        px, py = self._pos_calc(x, y, w, h, p)
        p.geometry(f"{w}x{h}+{px}+{py}")
        p.after(10, lambda: _apply_glass_effect(p))

        # Header
        tk.Label(
            p, text="✦ mouse.ai", font=_font(9, "bold"),
            fg=C["text_sec"], bg=C["bg"],
        ).pack(pady=(12, 0))

        # Animated text
        lbl = tk.Label(
            p, text="Thinking", font=_font(11),
            fg=C["text"], bg=C["bg"],
        )
        lbl.pack(pady=(4, 0))

        self._popup = p
        self._fade_in(p, 0)
        self._anim_loading(p, lbl, 0)

    def _anim_loading(self, p, lbl, step):
        if not p or not p.winfo_exists():
            return
        dots = "·" * (step % 4)
        try:
            lbl.configure(text=f"Thinking{dots}")
        except tk.TclError:
            return
        self.root.after(400, lambda: self._anim_loading(p, lbl, step + 1))

    # ── Response ────────────────────────────────────────────────────

    def _build_response(self, text, x, y):
        text = (text or "No response.").strip()

        p = tk.Toplevel(self.root)
        p.overrideredirect(True)
        p.attributes("-topmost", True)
        p.attributes("-alpha", 0.0)
        p.configure(bg=C["bg"])

        # ── Measure ──
        body_font = _font(11)
        max_text_w = self.MAX_W - self.PAD * 2 - 16
        content_w, content_h, line_count = _measure_text(text, body_font, max_text_w)

        header_h = 34
        footer_h = 38
        screen_h = p.winfo_screenheight()
        max_body_h = int(screen_h * self.MAX_H_RATIO) - header_h - footer_h - 20
        needs_scroll = content_h > max_body_h
        body_h = min(content_h, max_body_h) + 16

        popup_w = max(min(content_w + self.PAD * 2 + 16, self.MAX_W), self.MIN_W)
        popup_h = header_h + body_h + footer_h + 12

        px, py = self._pos_calc(x, y, popup_w, popup_h, p)
        p.geometry(f"{popup_w}x{popup_h}+{px}+{py}")
        p.after(10, lambda: _apply_glass_effect(p))

        # ── Border frame ──
        border = tk.Frame(p, bg=C["border"], padx=1, pady=1)
        border.pack(fill="both", expand=True)
        main = tk.Frame(border, bg=C["bg"])
        main.pack(fill="both", expand=True)

        # ── Header ──
        hdr = tk.Frame(main, bg=C["bg"], height=header_h)
        hdr.pack(fill="x", padx=self.PAD, pady=(10, 0))
        hdr.pack_propagate(False)

        tk.Label(
            hdr, text="✦", font=("Segoe UI", 12, "bold"),
            bg=C["bg"], fg=C["accent"],
        ).pack(side="left")
        tk.Label(
            hdr, text="  mouse.ai", font=_font(10, "bold"),
            bg=C["bg"], fg=C["text_sec"],
        ).pack(side="left")

        # Close button
        x_btn = tk.Label(
            hdr, text=" ✕ ", font=_font(11),
            bg=C["bg"], fg="#555555", cursor="hand2",
        )
        x_btn.pack(side="right")
        x_btn.bind("<Button-1>", lambda e: self._destroy_popup())
        x_btn.bind("<Enter>", lambda e: x_btn.configure(fg=C["close_hover"]))
        x_btn.bind("<Leave>", lambda e: x_btn.configure(fg="#555555"))

        # ── Separator ──
        tk.Frame(main, bg=C["sep"], height=1).pack(fill="x", padx=self.PAD, pady=(6, 6))

        # ── Body ──
        body = tk.Frame(main, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=self.PAD)

        if needs_scroll:
            txt = tk.Text(
                body, font=body_font,
                fg=C["text"], bg=C["bg"],
                wrap="word", relief="flat",
                borderwidth=0, highlightthickness=0,
                padx=4, pady=4, cursor="arrow",
                spacing1=2, spacing2=1, spacing3=3,
                selectbackground=C["accent"],
                selectforeground="#000000",
            )
            sb = tk.Scrollbar(
                body, orient="vertical", command=txt.yview,
                bg=C["surface"], troughcolor=C["bg"],
                activebackground=C["glow"],
                width=5, relief="flat",
            )
            txt.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y", pady=4)
            txt.pack(fill="both", expand=True)
            txt.insert("1.0", text)
            txt.configure(state="disabled")
        else:
            msg = tk.Message(
                body, text=text, font=body_font,
                fg=C["text"], bg=C["bg"],
                width=max_text_w, justify="left", anchor="nw",
            )
            msg.pack(fill="both", expand=True, pady=(2, 4))

        # ── Footer ──
        foot = tk.Frame(main, bg=C["bg"], height=footer_h)
        foot.pack(fill="x", padx=self.PAD, pady=(2, 10))

        # Copy button
        copy_box = tk.Frame(foot, bg=C["surface"], padx=10, pady=4,
                            highlightbackground=C["border"], highlightthickness=1)
        copy_lbl = tk.Label(
            copy_box, text="📋  Copy", font=_font(9),
            fg=C["text_sec"], bg=C["surface"], cursor="hand2",
        )
        copy_lbl.pack()

        def do_copy(e):
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            copy_lbl.configure(text="✓  Copied", fg=C["success"])
            self.root.after(1500, lambda: (
                copy_lbl.configure(text="📋  Copy", fg=C["text_sec"])
                if copy_lbl.winfo_exists() else None
            ))

        copy_box.pack(side="right", pady=(4, 0))
        copy_lbl.bind("<Button-1>", do_copy)
        copy_box.bind("<Button-1>", do_copy)

        def _enter(e):
            copy_box.configure(bg=C["hover"])
            copy_lbl.configure(bg=C["hover"])
        def _leave(e):
            copy_box.configure(bg=C["surface"])
            copy_lbl.configure(bg=C["surface"])
        copy_box.bind("<Enter>", _enter)
        copy_box.bind("<Leave>", _leave)
        copy_lbl.bind("<Enter>", _enter)
        copy_lbl.bind("<Leave>", _leave)

        self._popup = p
        self._fade_in(p, 0)
        self._dismiss_timer = self.root.after(self.auto_dismiss * 1000, self._fade_out_destroy)
        p.bind("<Escape>", lambda e: self._destroy_popup())

    # ── Positioning ─────────────────────────────────────────────────

    def _pos_calc(self, x, y, w, h, win):
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        px, py = x + 16, y + 16
        if px + w > sw - 12:
            px = x - w - 16
        if py + h > sh - 48:
            py = y - h - 16
        return max(8, px), max(8, py)

    # ── Animations ──────────────────────────────────────────────────

    def _fade_in(self, w, step):
        if not w or not w.winfo_exists():
            return
        a = min(0.97, step * 0.10)
        try:
            w.attributes("-alpha", a)
        except tk.TclError:
            return
        if a < 0.95:
            self.root.after(16, lambda: self._fade_in(w, step + 1))

    def _fade_out_destroy(self):
        if self._popup and self._popup.winfo_exists():
            self._fade_out(self._popup, 0.97)

    def _fade_out(self, w, a):
        if not w or not w.winfo_exists():
            return
        a -= 0.10
        if a <= 0:
            self._destroy_popup()
            return
        try:
            w.attributes("-alpha", a)
        except tk.TclError:
            return
        self.root.after(16, lambda: self._fade_out(w, a))

    def _destroy_popup(self):
        if self._dismiss_timer:
            try:
                self.root.after_cancel(self._dismiss_timer)
            except Exception:
                pass
            self._dismiss_timer = None
        if self._popup:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None
