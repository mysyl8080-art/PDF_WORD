"""Extract images / text from PDFs."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from .common import ToolError, cap_pages, open_reader, parse_ranges, safe_stem, unique_path
from .pdf_convert import extract_page_texts

Params = dict


def extract_images(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    r = open_reader(src)
    cap_pages(len(r.pages))
    stem = safe_stem(src)
    results: list[Path] = []
    for pno, page in enumerate(r.pages, 1):
        try:
            images = list(page.images)
        except Exception:
            continue
        for k, im in enumerate(images, 1):
            try:
                pil = Image.open(io.BytesIO(im.data))
                if pil.width < 24 or pil.height < 24:  # skip tiny decorations
                    continue
                ext = "png" if pil.mode in ("RGBA", "LA", "P", "1") else "jpg"
                dest = unique_path(out, f"{stem}_p{pno:03d}_img{k}.{ext}")
                if ext == "jpg":
                    pil.convert("RGB").save(dest, "JPEG", quality=95)
                else:
                    pil.save(dest, "PNG")
                results.append(dest)
            except Exception:
                continue
    if not results:
        raise ToolError("no_images")
    return results


def extract_text(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    r = open_reader(src)
    n = len(r.pages)
    idx = parse_ranges(str(p.get("pages", "all")), n, dedupe=True)
    texts = extract_page_texts(src, idx)
    if not any(t.strip() for t in texts):
        raise ToolError("scanned")
    body = "\n\n".join(f"──────── Page {i + 1} ────────\n{t}" for i, t in zip(idx, texts))
    dest = unique_path(out, f"{safe_stem(src)}_text.txt")
    dest.write_text(body, encoding="utf-8")
    return [dest]