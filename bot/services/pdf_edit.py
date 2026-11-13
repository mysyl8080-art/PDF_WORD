"""PDF editing: merge, split, extract/delete pages, rotate, reorder, page numbers, watermark."""
from __future__ import annotations

import io
import math
from pathlib import Path

import pypdf
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

from .common import ToolError, cap_pages, open_reader, parse_ranges, safe_stem, unique_path
from .fonts import font_name, shape

Params = dict


def _write(writer: pypdf.PdfWriter, dest: Path) -> Path:
    writer.add_metadata({"/Producer": "ToolsBot"})
    with open(dest, "wb") as fh:
        writer.write(fh)
    return dest


def merge_pdfs(files: list[Path], out: Path, p: Params) -> list[Path]:
    if len(files) < 2:
        raise ToolError("need_more_files")
    writer = pypdf.PdfWriter()
    total = 0
    for f in files:
        r = open_reader(f)
        total += len(r.pages)
        cap_pages(total)
        for page in r.pages:
            writer.add_page(page)
    return [_write(writer, unique_path(out, "merged.pdf"))]


def split_pdf(files: list[Path], out: Path, p: Params) -> list[Path]:
    """mode: 'all' → one file per page; else ranges like '1-3,4-6' → one file per range."""
    src = files[0]
    r = open_reader(src)
    n = len(r.pages)
    cap_pages(n)
    spec = str(p.get("ranges", "all")).strip()
    stem = safe_stem(src)
    results: list[Path] = []
    if spec.lower() in {"all", "الكل", "*"}:
        for i in range(n):
            w = pypdf.PdfWriter()
            w.add_page(r.pages[i])
            results.append(_write(w, unique_path(out, f"{stem}_page_{i + 1:03d}.pdf")))
    else:
        groups = [g for g in spec.replace("،", ",").split(",") if g.strip()]
        if not groups:
            raise ToolError("bad_pages", spec)
        for g in groups:
            idx = parse_ranges(g, n, allow_all=False)
            w = pypdf.PdfWriter()
            for i in idx:
                w.add_page(r.pages[i])
            label = g.strip().replace(" ", "")
            results.append(_write(w, unique_path(out, f"{stem}_pages_{label}.pdf")))
    return results


def extract_pages(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    r = open_reader(src)
    idx = parse_ranges(str(p.get("pages", "")), len(r.pages), allow_all=False, dedupe=True)
    w = pypdf.PdfWriter()
    for i in idx:
        w.add_page(r.pages[i])
    return [_write(w, unique_path(out, f"{safe_stem(src)}_extracted.pdf"))]


def delete_pages(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    r = open_reader(src)
    n = len(r.pages)
    remove = set(parse_ranges(str(p.get("pages", "")), n, allow_all=False))
    keep = [i for i in range(n) if i not in remove]
    if not keep:
        raise ToolError("bad_pages", "cannot delete all pages")
    w = pypdf.PdfWriter()
    for i in keep:
        w.add_page(r.pages[i])
    return [_write(w, unique_path(out, f"{safe_stem(src)}_edited.pdf"))]


def rotate_pdf(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    r = open_reader(src)
    n = len(r.pages)
    try:
        angle = int(p.get("angle", 90))
    except (TypeError, ValueError) as e:
        raise ToolError("bad_pages", "angle") from e
    if angle % 90 != 0:
        raise ToolError("bad_pages", "angle must be multiple of 90")
    targets = set(parse_ranges(str(p.get("pages", "all")), n))
    w = pypdf.PdfWriter()
    for i, page in enumerate(r.pages):
        if i in targets:
            page.rotate(angle)
        w.add_page(page)
    return [_write(w, unique_path(out, f"{safe_stem(src)}_rotated.pdf"))]


def reorder_pdf(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    r = open_reader(src)
    n = len(r.pages)
    order = parse_ranges(str(p.get("order", "")), n, allow_all=False)
    if sorted(order) != list(range(n)):
        raise ToolError("reorder", f"{n}")
    w = pypdf.PdfWriter()
    for i in order:
        w.add_page(r.pages[i])
    return [_write(w, unique_path(out, f"{safe_stem(src)}_reordered.pdf"))]


# ───────────────────────── overlays ─────────────────────────
def _overlay_pdf(width: float, height: float, draw) -> pypdf.PageObject:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    draw(c, width, height)
    c.save()
    buf.seek(0)
    return pypdf.PdfReader(buf).pages[0]


def add_page_numbers(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    r = open_reader(src)
    n = len(r.pages)
    cap_pages(n)
    pos = str(p.get("position", "bc"))
    fname = font_name()
    w = pypdf.PdfWriter()
    for i, page in enumerate(r.pages, 1):
        page.transfer_rotation_to_content()
        pw, ph = float(page.mediabox.width), float(page.mediabox.height)
        label = f"{i} / {n}"

        def draw(c, W, H, label=label):
            c.setFont(fname, 10)
            c.setFillColor(Color(0.2, 0.2, 0.2))
            margin = 24
            y = margin if pos.startswith("b") else H - margin - 8
            if pos.endswith("c"):
                c.drawCentredString(W / 2, y, label)
            elif pos.endswith("r"):
                c.drawRightString(W - margin, y, label)
            else:
                c.drawString(margin, y, label)

        page.merge_page(_overlay_pdf(pw, ph, draw))
        w.add_page(page)
    return [_write(w, unique_path(out, f"{safe_stem(src)}_numbered.pdf"))]


def add_watermark(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    text = str(p.get("text", "")).strip()
    if not text:
        raise ToolError("bad_pages", "empty watermark")
    text = text[:60]
    r = open_reader(src)
    cap_pages(len(r.pages))
    fname = font_name()
    shaped = shape(text)
    w = pypdf.PdfWriter()
    for page in r.pages:
        page.transfer_rotation_to_content()
        pw, ph = float(page.mediabox.width), float(page.mediabox.height)

        def draw(c, W, H):
            size = max(24, min(90, (min(W, H) * 0.9) / max(len(shaped), 1) * 1.6))
            c.saveState()
            c.setFillColor(Color(0.5, 0.5, 0.5, alpha=0.28))
            c.setFont(fname, size)
            c.translate(W / 2, H / 2)
            c.rotate(math.degrees(math.atan2(H, W)) * 0.8)
            c.drawCentredString(0, -size / 3, shaped)
            c.restoreState()

        page.merge_page(_overlay_pdf(pw, ph, draw))
        w.add_page(page)
    return [_write(w, unique_path(out, f"{safe_stem(src)}_watermarked.pdf"))]