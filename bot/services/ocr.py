"""OCR (Tesseract): scanned PDFs / images → searchable PDF + TXT + editable DOCX."""
from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

import pypdf
import pytesseract
from PIL import Image, ImageOps

from ..config import settings
from .common import ToolError, ext_of, has_binary, is_rtl_text, safe_stem, unique_path
from .pdf_convert import render_pages

Params = dict


@lru_cache(maxsize=1)
def _langs() -> str:
    if not has_binary("tesseract"):
        raise ToolError("unsupported", "tesseract not installed")
    installed = set(pytesseract.get_languages(config=""))
    wanted = [l for l in settings.ocr_langs.split("+") if l in installed]
    return "+".join(wanted) if wanted else ("eng" if "eng" in installed else next(iter(installed - {"osd"}), "eng"))


def _load_pages(src: Path):
    if ext_of(src) == "pdf":
        from .pdf_convert import open_pdfium

        n = len(open_pdfium(src))
        if n > settings.ocr_max_pages:
            raise ToolError("too_many_pages", f"{n}>{settings.ocr_max_pages}")
        for _, img in render_pages(src, dpi=300):
            yield img
    else:
        try:
            img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        except Exception as e:
            raise ToolError("bad_image", str(e)) from e
        yield img


def ocr_file(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    lang = _langs()
    stem = safe_stem(src)
    texts: list[str] = []
    writer = pypdf.PdfWriter()
    for img in _load_pages(src):
        gray = ImageOps.autocontrast(img.convert("L"))
        try:
            texts.append(pytesseract.image_to_string(gray, lang=lang, timeout=120).strip())
            pdf_bytes = pytesseract.image_to_pdf_or_hocr(img, lang=lang, extension="pdf", timeout=120)
        except RuntimeError as e:
            raise ToolError("timeout", str(e)) from e
        writer.append(pypdf.PdfReader(io.BytesIO(pdf_bytes)))

    if not any(texts):
        raise ToolError("no_text")

    results: list[Path] = []
    pdf_dest = unique_path(out, f"{stem}_ocr.pdf")
    with open(pdf_dest, "wb") as fh:
        writer.write(fh)
    results.append(pdf_dest)

    txt_dest = unique_path(out, f"{stem}_ocr.txt")
    txt_dest.write_text("\n\n".join(texts), encoding="utf-8")
    results.append(txt_dest)

    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement

    doc = Document()
    for i, t in enumerate(texts):
        if i:
            doc.add_page_break()
        for line in t.split("\n"):
            par = doc.add_paragraph(line)
            if is_rtl_text(line):
                par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                par._p.get_or_add_pPr().append(OxmlElement("w:bidi"))
    docx_dest = unique_path(out, f"{stem}_ocr.docx")
    doc.save(docx_dest)
    results.append(docx_dest)
    return results