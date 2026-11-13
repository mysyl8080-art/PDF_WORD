"""Tool registry — every feature of the bot is declared here (single source of truth)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .services import image_tools as img
from .services import ocr, pdf_convert as pc, pdf_edit as pe, pdf_extract as px, pdf_security as ps, to_pdf as tp

PDF = ("pdf",)
IMG_IN = ("jpg", "jpeg", "png", "webp", "bmp", "gif", "tif", "tiff", "heic", "heif")


@dataclass(frozen=True)
class ParamSpec:
    key: str
    prompt_ar: str
    prompt_en: str
    # (value, label_ar, label_en) → shown as buttons; empty → free-text reply
    choices: tuple[tuple[str, str, str], ...] = ()
    sensitive: bool = False  # delete the user's message after reading it (passwords)


@dataclass(frozen=True)
class Tool:
    key: str
    category: str
    icon: str
    name_ar: str
    name_en: str
    accepts: tuple[str, ...]
    func: Callable
    batch: bool = False              # collect many files, then press "Done"
    min_files: int = 1
    params: tuple[ParamSpec, ...] = ()
    allow_text: str | None = None    # extension used when the user sends plain text instead of a file

    def name(self, lang: str) -> str:
        return self.name_ar if lang == "ar" else self.name_en


CATEGORIES: list[tuple[str, str, str, str]] = [
    ("pdf_from", "📤", "تحويل من PDF", "Convert from PDF"),
    ("to_pdf", "📥", "تحويل إلى PDF", "Convert to PDF"),
    ("pdf_edit", "✂️", "تعديل PDF", "Edit PDF"),
    ("pdf_sec", "🔐", "حماية PDF", "PDF Security"),
    ("pdf_extract", "🧲", "استخراج و OCR", "Extract & OCR"),
    ("image", "🖼", "تحويل الصور", "Image Tools"),
]

PAGES_PARAM = lambda key, ar, en: ParamSpec(key, ar, en)  # noqa: E731

TOOLS: list[Tool] = [
    # ───────── PDF → X ─────────
    Tool("pdf2jpg", "pdf_from", "🖼", "PDF إلى JPG", "PDF to JPG", PDF, pc.pdf_to_jpg),
    Tool("pdf2png", "pdf_from", "🖼", "PDF إلى PNG", "PDF to PNG", PDF, pc.pdf_to_png),
    Tool("pdf2docx", "pdf_from", "📝", "PDF إلى Word", "PDF to Word (DOCX)", PDF, pc.pdf_to_docx),
    Tool("pdf2xlsx", "pdf_from", "📊", "PDF إلى Excel", "PDF to Excel", PDF, pc.pdf_to_xlsx),
    Tool("pdf2pptx", "pdf_from", "📽", "PDF إلى PowerPoint", "PDF to PowerPoint", PDF, pc.pdf_to_pptx),
    Tool("pdf2txt", "pdf_from", "📄", "PDF إلى TXT", "PDF to TXT", PDF, pc.pdf_to_txt),
    Tool("pdf2html", "pdf_from", "🌐", "PDF إلى HTML", "PDF to HTML", PDF, pc.pdf_to_html),
    Tool("pdf2epub", "pdf_from", "📚", "PDF إلى EPUB", "PDF to EPUB", PDF, pc.pdf_to_epub),
    # ───────── X → PDF ─────────
    Tool("img2pdf", "to_pdf", "🖼", "صور (JPG/PNG) إلى PDF", "JPG/PNG to PDF", IMG_IN, tp.images_to_pdf, batch=True),
    Tool("docx2pdf", "to_pdf", "📝", "Word إلى PDF", "Word to PDF", ("docx", "doc", "odt", "rtf"), tp.office_to_pdf),
    Tool("xlsx2pdf", "to_pdf", "📊", "Excel إلى PDF", "Excel to PDF", ("xlsx", "xls", "ods", "csv"), tp.office_to_pdf),
    Tool("pptx2pdf", "to_pdf", "📽", "PowerPoint إلى PDF", "PowerPoint to PDF", ("pptx", "ppt", "odp"), tp.office_to_pdf),
    Tool("txt2pdf", "to_pdf", "📄", "TXT إلى PDF", "TXT to PDF", ("txt", "md", "log"), tp.txt_to_pdf, allow_text="txt"),
    Tool("html2pdf", "to_pdf", "🌐", "HTML / رابط إلى PDF", "HTML / URL to PDF", ("html", "htm", "url"), tp.html_to_pdf, allow_text="html"),
    # ───────── Edit ─────────
    Tool("merge", "pdf_edit", "🔗", "دمج ملفات PDF", "Merge PDFs", PDF, pe.merge_pdfs, batch=True, min_files=2),
    Tool("split", "pdf_edit", "✂️", "تقسيم PDF", "Split PDF", PDF, pe.split_pdf, params=(
        ParamSpec("ranges",
                  "أرسل <b>all</b> لتقسيمه إلى صفحات منفصلة، أو نطاقات مثل: <code>1-3,4-6,7</code> (كل نطاق ملف مستقل).",
                  "Send <b>all</b> to split into single pages, or ranges like <code>1-3,4-6,7</code> (one file per range)."),)),
    Tool("extract_pages", "pdf_edit", "📑", "استخراج صفحات محددة", "Extract pages", PDF, pe.extract_pages, params=(
        ParamSpec("pages", "أرسل أرقام الصفحات المطلوبة، مثال: <code>1-3,5,8-</code>",
                  "Send the pages to extract, e.g. <code>1-3,5,8-</code>"),)),
    Tool("delete_pages", "pdf_edit", "🗑", "حذف صفحات", "Delete pages", PDF, pe.delete_pages, params=(
        ParamSpec("pages", "أرسل أرقام الصفحات التي تريد حذفها، مثال: <code>2,4-6</code>",
                  "Send the pages to delete, e.g. <code>2,4-6</code>"),)),
    Tool("rotate", "pdf_edit", "🔄", "تدوير صفحات", "Rotate pages", PDF, pe.rotate_pdf, params=(
        ParamSpec("angle", "اختر زاوية التدوير:", "Choose rotation angle:",
                  (("90", "↻ 90°", "↻ 90°"), ("180", "↻ 180°", "↻ 180°"), ("270", "↺ 90°", "↺ 90°"))),
        ParamSpec("pages", "أي صفحات؟ أرسل <b>all</b> للكل أو نطاقًا مثل <code>1-3,5</code>",
                  "Which pages? Send <b>all</b> or a range like <code>1-3,5</code>"))),
    Tool("reorder", "pdf_edit", "🔀", "إعادة ترتيب الصفحات", "Reorder pages", PDF, pe.reorder_pdf, params=(
        ParamSpec("order", "أرسل الترتيب الجديد لكل الصفحات، مثال لملف من 4 صفحات: <code>3,1,2,4</code>",
                  "Send the new order of ALL pages, e.g. for 4 pages: <code>3,1,2,4</code>"),)),
    Tool("page_numbers", "pdf_edit", "🔢", "إضافة أرقام الصفحات", "Add page numbers", PDF, pe.add_page_numbers, params=(
        ParamSpec("position", "اختر موضع الترقيم:", "Choose number position:",
                  (("bc", "أسفل المنتصف", "Bottom center"), ("br", "أسفل اليمين", "Bottom right"),
                   ("bl", "أسفل اليسار", "Bottom left"), ("tc", "أعلى المنتصف", "Top center"))),)),
    Tool("watermark", "pdf_edit", "💧", "إضافة Watermark", "Add watermark", PDF, pe.add_watermark, params=(
        ParamSpec("text", "اكتب نص العلامة المائية (حتى 60 حرفًا):", "Type the watermark text (max 60 chars):"),)),
    # ───────── Security ─────────
    Tool("protect", "pdf_sec", "🔒", "حماية PDF بكلمة مرور", "Protect PDF with password", PDF, ps.protect_pdf, params=(
        ParamSpec("password", "اكتب كلمة المرور (4 أحرف على الأقل). سأحذف رسالتك فور قراءتها.",
                  "Type a password (min 4 chars). I'll delete your message right away.", sensitive=True),)),
    Tool("unlock", "pdf_sec", "🔓", "إزالة كلمة المرور", "Remove password", PDF, ps.unlock_pdf, params=(
        ParamSpec("password", "اكتب كلمة المرور الحالية للملف (أو <b>-</b> إن كان مقيّدًا للتعديل/الطباعة فقط). "
                              "<i>يعمل فقط للملفات التي تملك صلاحية فتحها.</i>",
                  "Type the file's current password (or <b>-</b> if it only has edit/print restrictions). "
                  "<i>Works only for files you're authorized to open.</i>", sensitive=True),)),
    # ───────── Extract / OCR ─────────
    Tool("extract_images", "pdf_extract", "🧩", "استخراج الصور من PDF", "Extract images from PDF", PDF, px.extract_images),
    Tool("extract_text", "pdf_extract", "🔤", "استخراج النصوص من PDF", "Extract text from PDF", PDF, px.extract_text, params=(
        ParamSpec("pages", "أي صفحات؟ أرسل <b>all</b> للكل أو نطاقًا مثل <code>1-5</code>",
                  "Which pages? Send <b>all</b> or a range like <code>1-5</code>"),)),
    Tool("ocr", "pdf_extract", "👁", "OCR — صور/ممسوح ضوئيًا إلى نص", "OCR — scanned/image to text",
         PDF + IMG_IN, ocr.ocr_file),
    # ───────── Images ─────────
    Tool("jpg2png", "image", "🖼", "JPG إلى PNG", "JPG to PNG", ("jpg", "jpeg"), img.to_png, batch=True),
    Tool("png2jpg", "image", "🖼", "PNG إلى JPG", "PNG to JPG", ("png",), img.to_jpg, batch=True),
    Tool("webp2jpg", "image", "🖼", "WEBP إلى JPG", "WEBP to JPG", ("webp",), img.to_jpg, batch=True),
    Tool("webp2png", "image", "🖼", "WEBP إلى PNG", "WEBP to PNG", ("webp",), img.to_png, batch=True),
    Tool("to_webp", "image", "🖼", "JPG/PNG إلى WEBP", "JPG/PNG to WEBP", ("jpg", "jpeg", "png"), img.to_webp, batch=True),
    Tool("any2jpg", "image", "📷", "HEIC/BMP/GIF/TIFF إلى JPG", "HEIC/BMP/GIF/TIFF to JPG",
         ("heic", "heif", "bmp", "gif", "tif", "tiff"), img.to_jpg, batch=True),
    Tool("compress", "image", "🗜", "ضغط الصور", "Compress images", IMG_IN, img.compress_images, batch=True, params=(
        ParamSpec("quality", "اختر مستوى الجودة:", "Choose quality:",
                  (("85", "عالية 85", "High 85"), ("70", "متوسطة 70", "Medium 70"), ("50", "أقل حجم 50", "Smallest 50"))),)),
    Tool("resize", "image", "📐", "تغيير حجم الصور", "Resize images", IMG_IN, img.resize_images, batch=True, params=(
        ParamSpec("width", "اكتب العرض الجديد بالبكسل (مثل <code>800</code>) أو نسبة (مثل <code>50%</code>). النسبة محفوظة تلقائيًا.",
                  "Type the new width in px (e.g. <code>800</code>) or a percentage (e.g. <code>50%</code>). Aspect ratio is kept."),)),
]

TOOL_MAP: dict[str, Tool] = {t.key: t for t in TOOLS}


def tools_in(category: str) -> list[Tool]:
    return [t for t in TOOLS if t.category == category]


def tools_for_ext(ext: str) -> list[Tool]:
    """Smart suggestions when a file is sent without picking a tool first."""
    return [t for t in TOOLS if ext.lower() in t.accepts]