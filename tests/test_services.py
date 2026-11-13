"""Service-level tests (no Telegram needed). Run: pytest -q"""
import zipfile
from pathlib import Path

import pypdf
import pytest
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from bot.services import image_tools as img
from bot.services import pdf_convert as pc
from bot.services import pdf_edit as pe
from bot.services import pdf_extract as px
from bot.services import pdf_security as ps
from bot.services import to_pdf as tp
from bot.services.common import ToolError, parse_ranges


@pytest.fixture()
def pdf(tmp_path) -> Path:
    p = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(p), pagesize=A4)
    for i in range(1, 5):
        c.setFont("Helvetica", 18)
        c.drawString(72, 750, f"Hello page {i}")
        c.drawString(72, 700, "Line two of text for extraction")
        c.showPage()
    c.save()
    return p


@pytest.fixture()
def png(tmp_path) -> Path:
    p = tmp_path / "pic.png"
    Image.new("RGBA", (200, 120), (255, 0, 0, 128)).save(p)
    return p


@pytest.fixture()
def out(tmp_path) -> Path:
    d = tmp_path / "out"
    d.mkdir()
    return d


def npages(p: Path) -> int:
    return len(pypdf.PdfReader(str(p)).pages)


# ── helpers
def test_parse_ranges():
    assert parse_ranges("1-3,5", 10) == [0, 1, 2, 4]
    assert parse_ranges("٢-٣", 5) == [1, 2]
    assert parse_ranges("8-", 10) == [7, 8, 9]
    assert parse_ranges("all", 3) == [0, 1, 2]
    assert parse_ranges("1,1,2", 3, dedupe=True) == [0, 1]
    with pytest.raises(ToolError):
        parse_ranges("9", 3)
    with pytest.raises(ToolError):
        parse_ranges("abc", 3)


# ── PDF → X
def test_pdf_to_images(pdf, out):
    assert len(pc.pdf_to_jpg([pdf], out, {})) == 4
    assert all(f.suffix == ".png" for f in pc.pdf_to_png([pdf], out, {}))


def test_pdf_to_txt_html_epub(pdf, out):
    t = pc.pdf_to_txt([pdf], out, {})[0]
    assert "Hello page 1" in t.read_text()
    h = pc.pdf_to_html([pdf], out, {})[0]
    assert "<html" in h.read_text()
    e = pc.pdf_to_epub([pdf], out, {})[0]
    with zipfile.ZipFile(e) as z:
        assert z.namelist()[0] == "mimetype"
        assert z.read("mimetype") == b"application/epub+zip"
        assert "OEBPS/content.opf" in z.namelist()


def test_pdf_to_docx_xlsx_pptx(pdf, out):
    assert pc.pdf_to_docx([pdf], out, {})[0].stat().st_size > 1000
    assert pc.pdf_to_xlsx([pdf], out, {})[0].suffix == ".xlsx"
    from pptx import Presentation

    pp = pc.pdf_to_pptx([pdf], out, {})[0]
    assert len(Presentation(str(pp)).slides) == 4


# ── X → PDF
def test_images_to_pdf(png, out, tmp_path):
    p2 = tmp_path / "b.png"
    Image.new("RGB", (50, 50), "blue").save(p2)
    res = tp.images_to_pdf([png, p2], out, {})[0]
    assert npages(res) == 2


def test_txt_to_pdf(tmp_path, out):
    f = tmp_path / "note.txt"
    f.write_text("مرحبا بالعالم\\nHello world", encoding="utf-8")
    res = tp.txt_to_pdf([f], out, {})[0]
    assert npages(res) >= 1


def test_html_to_pdf(tmp_path, out):
    f = tmp_path / "page.html"
    f.write_text("<h1>Title</h1><p>Body</p>", encoding="utf-8")
    assert npages(tp.html_to_pdf([f], out, {})[0]) >= 1


def test_office_to_pdf(tmp_path, out):
    from docx import Document

    d = Document()
    d.add_paragraph("Word → PDF")
    f = tmp_path / "doc.docx"
    d.save(f)
    assert npages(tp.office_to_pdf([f], out, {})[0]) >= 1


def test_url_blocked():
    for bad in ("http://127.0.0.1/", "http://localhost/", "http://169.254.169.254/", "file:///etc/passwd", "http://10.0.0.1/"):
        with pytest.raises(ToolError):
            tp.validate_url(bad)


# ── edit
def test_merge_split_extract_delete(pdf, out):
    assert npages(pe.merge_pdfs([pdf, pdf], out, {})[0]) == 8
    assert len(pe.split_pdf([pdf], out, {"ranges": "all"})) == 4
    parts = pe.split_pdf([pdf], out, {"ranges": "1-2,3-4"})
    assert [npages(x) for x in parts] == [2, 2]
    assert npages(pe.extract_pages([pdf], out, {"pages": "2-3"})[0]) == 2
    assert npages(pe.delete_pages([pdf], out, {"pages": "1"})[0]) == 3
    with pytest.raises(ToolError):
        pe.delete_pages([pdf], out, {"pages": "1-4"})


def test_rotate_reorder(pdf, out):
    r = pypdf.PdfReader(str(pe.rotate_pdf([pdf], out, {"angle": "90", "pages": "1"})[0]))
    assert r.pages[0].rotation == 90 and r.pages[1].rotation == 0
    res = pe.reorder_pdf([pdf], out, {"order": "4,3,2,1"})[0]
    assert "page 4" in pypdf.PdfReader(str(res)).pages[0].extract_text()
    with pytest.raises(ToolError):
        pe.reorder_pdf([pdf], out, {"order": "1,2"})


def test_numbers_watermark(pdf, out):
    n = pe.add_page_numbers([pdf], out, {"position": "bc"})[0]
    assert "1 / 4" in pypdf.PdfReader(str(n)).pages[0].extract_text()
    w = pe.add_watermark([pdf], out, {"text": "CONFIDENTIAL"})[0]
    assert "CONFIDENTIAL" in pypdf.PdfReader(str(w)).pages[0].extract_text()
    assert npages(pe.add_watermark([pdf], out, {"text": "سري للغاية"})[0]) == 4  # Arabic must not crash


# ── security
def test_protect_unlock(pdf, out):
    locked = ps.protect_pdf([pdf], out, {"password": "secret1"})[0]
    assert pypdf.PdfReader(str(locked)).is_encrypted
    with pytest.raises(ToolError):
        ps.unlock_pdf([locked], out, {"password": "wrong"})
    free = ps.unlock_pdf([locked], out, {"password": "secret1"})[0]
    assert not pypdf.PdfReader(str(free)).is_encrypted
    with pytest.raises(ToolError):
        ps.protect_pdf([pdf], out, {"password": "12"})


# ── extract
def test_extract_text_and_images(pdf, out, png):
    assert "Hello page 2" in px.extract_text([pdf], out, {"pages": "2"})[0].read_text()
    with pytest.raises(ToolError) as e:
        px.extract_images([pdf], out, {})
    assert e.value.code == "no_images"
    imgpdf = tp.images_to_pdf([png], out, {})[0]
    assert px.extract_images([imgpdf], out, {})


# ── images
def test_image_converters(png, out, tmp_path):
    j = img.to_jpg([png], out, {})[0]
    assert Image.open(j).format == "JPEG"
    assert Image.open(img.to_png([j], out, {})[0]).format == "PNG"
    assert Image.open(img.to_webp([png], out, {})[0]).format == "WEBP"
    assert Image.open(img.resize_images([png], out, {"width": "100"})[0]).width == 100
    assert Image.open(img.resize_images([png], out, {"width": "50%"})[0]).width == 100
    assert img.compress_images([png], out, {"quality": "50"})[0].suffix == ".jpg"
    bad = tmp_path / "x.png"
    bad.write_bytes(b"not an image")
    with pytest.raises(ToolError):
        img.to_jpg([bad], out, {})


# ── OCR (skipped if tesseract missing)
def test_ocr(out, tmp_path):
    from bot.services.common import has_binary

    if not has_binary("tesseract"):
        pytest.skip("tesseract not installed")
    from PIL import ImageDraw, ImageFont

    im = Image.new("RGB", (900, 200), "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
    d.text((20, 50), "HELLO OCR TEST", fill="black", font=f)
    p = tmp_path / "scan.png"
    im.save(p)
    from bot.services import ocr

    res = ocr.ocr_file([p], out, {})
    assert {r.suffix for r in res} == {".pdf", ".txt", ".docx"}
    assert "HELLO" in [r for r in res if r.suffix == ".txt"][0].read_text().upper()
