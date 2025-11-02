"""Font registration helpers."""

import os

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def safe_register_mono_font() -> tuple[str, float]:
    """
    Try to register a preferred monospace font, falling back to Courier.
    Returns (font_name, ascent_adjust).
    """
    candidates = [
        ("DejaVuSansMono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        (
            "LiberationMono",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        ),
        (
            "JetBrainsMono",
            "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf",
        ),
        ("UbuntuMono", "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf"),
    ]
    for name, path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name, 0.0
            except Exception:
                continue
    return "Courier", 0.0
