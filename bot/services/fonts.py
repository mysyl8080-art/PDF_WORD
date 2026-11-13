"""Font discovery + Arabic text shaping for ReportLab overlays."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/amiri/Amiri-Regular.ttf",
    "/usr/share/fonts/truetype/kacst/KacstOne.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


@lru_cache(maxsize=1)
def font_name() -> str:
    """Register & return the best available Unicode font name (falls back to Helvetica)."""
    for c in _CANDIDATES:
        if Path(c).exists():
            try:
                pdfmetrics.registerFont(TTFont("ToolsFont", c))
                return "ToolsFont"
            except Exception:
                continue
    return "Helvetica"


def shape(text: str) -> str:
    """Reshape + reorder Arabic so ReportLab draws it correctly (no-op if libs missing)."""
    if not any("\u0600" <= ch <= "\u06FF" for ch in text):
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text