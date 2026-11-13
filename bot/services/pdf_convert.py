"""PDF → other formats (JPG, PNG, DOCX, XLSX, PPTX, TXT, HTML, EPUB)."""
from __future__ import annotations

import html
import uuid
import zipfile
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium

from .common import ToolError, cap_pages, is_rtl_text, open_reader, safe_stem, unique_path

Params = dict


# ───────────────────────── helpers ─────────────────────────
def open_pdfium(path: Path, password: str | None = None) -> pdfium.PdfDocument:
    try:
        return pdfium.PdfDocument(str(path), password=password)
    except pdfium.PdfiumError as e:
        msg = str(e).lower()
        raise ToolError("encrypted" if "password" in msg else "bad_pdf", str(e)) from e


def render_pages(path: Path, dpi: int = 150, indexes: list[int] | None = None):
    """Yield (page_index, PIL.Image) for each requested page."""
    pdf = open_pdfium(path)
    try:
        total = len(pdf)
        cap_pages(total)
        for i in indexes if indexes is not None else range(total):
            page = pdf[i]
            try:
                yield i, page.render(scale=dpi / 72).to_pil().convert("RGB")
            finally:
                page.close()
    finally:
        pdf.close()


def extract_page_texts(path: Path, indexes: list[int] | None = None) -> list[str]:
    try:
        with pdfplumber.open(str(path)) as pdf:
            cap_pages(len(pdf.pages))
            pages = pdf.pages if indexes is None else [pdf.pages[i] for i in indexes]
            return [(p.extract_text() or "").strip() for p in pages]
    except ToolError:
        raise
    except Exception as e:
        msg = str(e).lower()
        raise ToolError("encrypted" if "password" in msg or "encrypt" in msg else "bad_pdf", str(e)) from e


def _require_text(texts: list[str]) -> None:
    if not any(t.strip() for t in texts):
        raise ToolError("scanned")


# ───────────────────────── to images ─────────────────────────
def _pdf_to_images(files: list[Path], out: Path, fmt: str) -> list[Path]:
    src = files[0]
    stem = safe_stem(src)
    results: list[Path] = []
    for i, img in render_pages(src, dpi=150):
        dest = unique_path(out, f"{stem}_page_{i + 1:03d}.{ 'jpg' if fmt == 'JPEG' else 'png'}")
        if fmt == "JPEG":
            img.save(dest, "JPEG", quality=92, optimize=True)
        else:
            img.save(dest, "PNG", optimize=True)
        results.append(dest)
    return results


def pdf_to_jpg(files: list[Path], out: Path, p: Params) -> list[Path]:
    return _pdf_to_images(files, out, "JPEG")


def pdf_to_png(files: list[Path], out: Path, p: Params) -> list[Path]:
    return _pdf_to_images(files, out, "PNG")


# ───────────────────────── to text ─────────────────────────
def pdf_to_txt(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    texts = extract_page_texts(src)
    _require_text(texts)
    body = "\n\n".join(f"──────── Page {i + 1} ────────\n{t}" for i, t in enumerate(texts))
    dest = unique_path(out, f"{safe_stem(src)}.txt")
    dest.write_text(body, encoding="utf-8")
    return [dest]


# ───────────────────────── to DOCX ─────────────────────────
def pdf_to_docx(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    dest = unique_path(out, f"{safe_stem(src)}.docx")
    open_reader(src)  # validates + checks encryption
    texts = extract_page_texts(src)
    _require_text(texts)

    try:  # best fidelity (layout, tables, images) for digital PDFs
        from pdf2docx import Converter

        cv = Converter(str(src))
        try:
            cv.convert(str(dest))
        finally:
            cv.close()
        if dest.exists() and dest.stat().st_size > 0:
            return [dest]
    except ImportError:
        pass
    except Exception:
        dest.unlink(missing_ok=True)

    # Fallback: text + tables via pdfplumber
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    doc = Document()
    with pdfplumber.open(str(src)) as pdf:
        for n, page in enumerate(pdf.pages):
            if n:
                doc.add_page_break()
            for para in (page.extract_text() or "").split("\n"):
                par = doc.add_paragraph(para)
                if is_rtl_text(para):
                    par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    ppr = par._p.get_or_add_pPr()
                    bidi = OxmlElement("w:bidi")
                    ppr.append(bidi)
            for table in page.extract_tables():
                if not table or not table[0]:
                    continue
                t = doc.add_table(rows=len(table), cols=len(table[0]))
                t.style = "Table Grid"
                for r, row in enumerate(table):
                    for c, cell in enumerate(row[: len(table[0])]):
                        t.cell(r, c).text = cell or ""
    doc.save(dest)
    return [dest]


# ───────────────────────── to XLSX ─────────────────────────
def pdf_to_xlsx(files: list[Path], out: Path, p: Params) -> list[Path]:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    src = files[0]
    wb = Workbook()
    wb.remove(wb.active)
    found_tables = 0
    all_text: list[tuple[int, str]] = []
    try:
        with pdfplumber.open(str(src)) as pdf:
            cap_pages(len(pdf.pages))
            for pno, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                for tno, table in enumerate(tables, 1):
                    if not table:
                        continue
                    found_tables += 1
                    ws = wb.create_sheet(f"P{pno}_T{tno}"[:31])
                    for row in table:
                        ws.append([(c or "").strip() for c in row])
                    for cell in ws[1]:
                        cell.font = Font(bold=True)
                    for col in ws.columns:
                        width = max((len(str(c.value or "")) for c in col), default=8)
                        ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 8), 60)
                    for row in ws.iter_rows():
                        for c in row:
                            c.alignment = Alignment(wrap_text=True, vertical="top")
                text = page.extract_text() or ""
                all_text.extend((pno, line) for line in text.split("\n") if line.strip())
    except ToolError:
        raise
    except Exception as e:
        raise ToolError("bad_pdf", str(e)) from e

    if not found_tables:
        if not all_text:
            raise ToolError("scanned")
        ws = wb.create_sheet("Text")
        ws.append(["Page", "Text"])
        for pno, line in all_text:
            ws.append([pno, line])
        ws.column_dimensions["B"].width = 100
    dest = unique_path(out, f"{safe_stem(src)}.xlsx")
    wb.save(dest)
    return [dest]


# ───────────────────────── to PPTX ─────────────────────────
def pdf_to_pptx(files: list[Path], out: Path, p: Params) -> list[Path]:
    """One slide per page (page rendered as high-quality image; extracted text kept in notes)."""
    from pptx import Presentation
    from pptx.util import Emu

    src = files[0]
    texts = extract_page_texts(src)
    prs = Presentation()
    first = True
    for i, img in render_pages(src, dpi=170):
        if first:
            w_emu = Emu(int(img.width / 170 * 914400))
            h_emu = Emu(int(img.height / 170 * 914400))
            prs.slide_width, prs.slide_height = w_emu, h_emu
            first = False
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        tmp = out / f".tmp_{uuid.uuid4().hex}.jpg"
        img.save(tmp, "JPEG", quality=90)
        slide.shapes.add_picture(str(tmp), 0, 0, prs.slide_width, prs.slide_height)
        tmp.unlink(missing_ok=True)
        if i < len(texts) and texts[i]:
            slide.notes_slide.notes_text_frame.text = texts[i]
    dest = unique_path(out, f"{safe_stem(src)}.pptx")
    prs.save(dest)
    return [dest]


# ───────────────────────── to HTML ─────────────────────────
def _html_doc(title: str, body: str, rtl: bool) -> str:
    d = "rtl" if rtl else "ltr"
    return f"""<!DOCTYPE html>
<html lang="{'ar' if rtl else 'en'}" dir="{d}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body{{font-family:'Segoe UI',Tahoma,'Noto Naskh Arabic',Arial,sans-serif;max-width:880px;margin:2rem auto;padding:0 1rem;line-height:1.8;color:#222}}
section.page{{border-bottom:1px dashed #bbb;padding:1rem 0}} h2{{font-size:.85rem;color:#888;font-weight:400}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}} td,th{{border:1px solid #ccc;padding:6px 8px}}
</style></head><body>
{body}
</body></html>"""


def pdf_to_html(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    parts: list[str] = []
    all_text = ""
    try:
        with pdfplumber.open(str(src)) as pdf:
            cap_pages(len(pdf.pages))
            for n, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                all_text += text
                paras = "".join(f"<p>{html.escape(l)}</p>" for l in text.split("\n") if l.strip())
                tables = ""
                for tb in page.extract_tables():
                    rows = "".join(
                        "<tr>" + "".join(f"<td>{html.escape(c or '')}</td>" for c in r) + "</tr>" for r in tb
                    )
                    tables += f"<table>{rows}</table>"
                parts.append(f'<section class="page"><h2>Page {n}</h2>{paras}{tables}</section>')
    except ToolError:
        raise
    except Exception as e:
        raise ToolError("bad_pdf", str(e)) from e
    if not all_text.strip():
        raise ToolError("scanned")
    dest = unique_path(out, f"{safe_stem(src)}.html")
    dest.write_text(_html_doc(safe_stem(src), "\n".join(parts), is_rtl_text(all_text)), encoding="utf-8")
    return [dest]


# ───────────────────────── to EPUB (no external lib) ─────────────────────────
def pdf_to_epub(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    texts = extract_page_texts(src)
    _require_text(texts)
    rtl = is_rtl_text("".join(texts))
    lang = "ar" if rtl else "en"
    title = safe_stem(src)
    book_id = f"urn:uuid:{uuid.uuid4()}"

    # group ~3 pages per chapter to keep a usable TOC
    chapters: list[tuple[str, str]] = []
    step = 3
    for i in range(0, len(texts), step):
        chunk = texts[i : i + step]
        body = "".join(
            f"<p>{html.escape(line)}</p>" for t in chunk for line in t.split("\n") if line.strip()
        )
        name = f"Pages {i + 1}-{min(i + step, len(texts))}"
        chapters.append((name, body))

    def xhtml(t: str, body: str) -> str:
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}" lang="{lang}" dir="{"rtl" if rtl else "ltr"}">'
            f"<head><title>{html.escape(t)}</title><link rel=\"stylesheet\" type=\"text/css\" href=\"style.css\"/></head>"
            f"<body><h2>{html.escape(t)}</h2>{body}</body></html>"
        )

    manifest = "".join(
        f'<item id="c{i}" href="c{i}.xhtml" media-type="application/xhtml+xml"/>' for i in range(len(chapters))
    )
    spine = "".join(f'<itemref idref="c{i}"/>' for i in range(len(chapters)))
    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="{lang}">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">{book_id}</dc:identifier><dc:title>{html.escape(title)}</dc:title><dc:language>{lang}</dc:language>
<meta property="dcterms:modified">2024-01-01T00:00:00Z</meta></metadata>
<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="css" href="style.css" media-type="text/css"/>{manifest}</manifest>
<spine{' page-progression-direction="rtl"' if rtl else ''}>{spine}</spine></package>"""
    nav_items = "".join(f'<li><a href="c{i}.xhtml">{html.escape(n)}</a></li>' for i, (n, _) in enumerate(chapters))
    nav = (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
        f'<head><title>TOC</title></head><body><nav epub:type="toc"><ol>{nav_items}</ol></nav></body></html>'
    )
    css = "body{line-height:1.7;font-family:serif}p{margin:.6em 0}" + ("body{direction:rtl;text-align:right}" if rtl else "")
    container = (
        '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
    )
    dest = unique_path(out, f"{title}.epub")
    with zipfile.ZipFile(dest, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)  # must be first, uncompressed
        z.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/nav.xhtml", nav, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/style.css", css, compress_type=zipfile.ZIP_DEFLATED)
        for i, (n, body) in enumerate(chapters):
            z.writestr(f"OEBPS/c{i}.xhtml", xhtml(n, body), compress_type=zipfile.ZIP_DEFLATED)
    return [dest]