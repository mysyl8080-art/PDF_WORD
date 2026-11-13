"""Password protect / unlock PDFs (unlock requires the legitimate password — no cracking)."""
from __future__ import annotations

from pathlib import Path

import pikepdf

from .common import ToolError, safe_stem, unique_path

Params = dict


def protect_pdf(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    pw = str(p.get("password", ""))
    if len(pw) < 4:
        raise ToolError("weak_password")
    try:
        with pikepdf.open(src) as pdf:
            dest = unique_path(out, f"{safe_stem(src)}_protected.pdf")
            pdf.save(dest, encryption=pikepdf.Encryption(user=pw, owner=pw + "#owner", R=6))
    except pikepdf.PasswordError as e:
        raise ToolError("encrypted") from e
    except pikepdf.PdfError as e:
        raise ToolError("bad_pdf", str(e)) from e
    return [dest]


def unlock_pdf(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    pw = str(p.get("password", "")).strip()
    if pw in {"-", "0", "none", "لا يوجد"}:
        pw = ""
    try:
        with pikepdf.open(src, password=pw) as pdf:
            dest = unique_path(out, f"{safe_stem(src)}_unlocked.pdf")
            pdf.save(dest)  # saved without encryption
    except pikepdf.PasswordError as e:
        raise ToolError("wrong_password") from e
    except pikepdf.PdfError as e:
        raise ToolError("bad_pdf", str(e)) from e
    return [dest]