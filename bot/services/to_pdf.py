"""Anything → PDF (images, Office, TXT, HTML/URL)."""
from __future__ import annotations

import html
import ipaddress
import shutil
import socket
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageOps

from ..config import settings
from .common import ToolError, has_binary, is_rtl_text, read_text_file, run_cmd, safe_stem, unique_path

Params = dict

# ───────────────────────── images → PDF ─────────────────────────
def images_to_pdf(files: list[Path], out: Path, p: Params) -> list[Path]:
    pages: list[Image.Image] = []
    try:
        for f in files:
            img = Image.open(f)
            img = ImageOps.exif_transpose(img)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                bg = Image.new("RGB", img.size, "white")
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
            pages.append(img)
    except Exception as e:
        raise ToolError("bad_image", str(e)) from e
    if not pages:
        raise ToolError("bad_image")
    name = safe_stem(files[0]) if len(files) == 1 else "images"
    dest = unique_path(out, f"{name}.pdf")
    pages[0].save(dest, "PDF", save_all=True, append_images=pages[1:], resolution=150.0, quality=95)
    return [dest]


# ───────────────────────── Office → PDF (LibreOffice) ─────────────────────────
def office_to_pdf(files: list[Path], out: Path, p: Params) -> list[Path]:
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        raise ToolError("unsupported", "LibreOffice not installed")
    src = files[0]
    with tempfile.TemporaryDirectory(prefix="lo_") as profile, tempfile.TemporaryDirectory(prefix="lo_out_") as tmp_out:
        # separate profile per job → safe concurrency
        cmd = [
            exe, f"-env:UserInstallation=file://{profile}", "--headless", "--norestore",
            "--convert-to", "pdf", "--outdir", tmp_out, str(src),
        ]
        res = run_cmd(cmd, timeout=settings.job_timeout)
        produced = list(Path(tmp_out).glob("*.pdf"))
        if res.returncode != 0 or not produced:
            raise ToolError("convert_failed", (res.stderr or res.stdout)[-300:])
        dest = unique_path(out, f"{safe_stem(src)}.pdf")
        shutil.move(str(produced[0]), dest)
    return [dest]


# ───────────────────────── HTML → PDF ─────────────────────────
def _is_public_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False
    return True


def validate_url(url: str) -> str:
    u = urlparse(url.strip())
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ToolError("url_blocked", "scheme")
    if not settings.allow_url_fetch or not _is_public_host(u.hostname):
        raise ToolError("url_blocked", u.hostname or "")
    return u.geturl()


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)  # re-check every hop (anti-SSRF)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch_html(url: str, limit: int = 5_000_000) -> str:
    url = validate_url(url)
    opener = urllib.request.build_opener(_SafeRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 ToolsBot"})
    try:
        with opener.open(req, timeout=20) as r:
            data = r.read(limit + 1)
            charset = r.headers.get_content_charset() or "utf-8"
    except ToolError:
        raise
    except Exception as e:
        raise ToolError("convert_failed", str(e)) from e
    if len(data) > limit:
        raise ToolError("convert_failed", "page too large")
    return data.decode(charset, errors="replace")


def _safe_url_fetcher(url: str, *args, **kwargs):
    """WeasyPrint fetcher: allow data:/public http(s) only (blocks file:// and internal hosts)."""
    from weasyprint import default_url_fetcher

    if url.startswith("data:"):
        return default_url_fetcher(url)
    u = urlparse(url)
    if u.scheme in ("http", "https") and settings.allow_url_fetch and u.hostname and _is_public_host(u.hostname):
        return default_url_fetcher(url)
    raise ValueError("blocked resource")


def _render_html(html_text: str, dest: Path, base_url: str | None = None) -> None:
    try:
        from weasyprint import HTML

        HTML(string=html_text, base_url=base_url, url_fetcher=_safe_url_fetcher).write_pdf(str(dest))
        return
    except ImportError:
        pass
    except Exception as e:
        raise ToolError("convert_failed", str(e)) from e
    # Fallback: wkhtmltopdf (dev environments)
    if not has_binary("wkhtmltopdf"):
        raise ToolError("unsupported", "no HTML renderer (install weasyprint)")
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "in.html"
        src.write_text(html_text, encoding="utf-8")
        res = run_cmd(["wkhtmltopdf", "--quiet", "--disable-local-file-access", "--encoding", "utf-8", "--no-images" if base_url else "--enable-local-file-access", str(src), str(dest)], timeout=settings.job_timeout)
    if not dest.exists():
        # wkhtmltopdf exits non-zero on minor resource errors but still writes output
        raise ToolError("convert_failed", res.stderr[-300:])


def html_to_pdf(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    if src.suffix.lower() == ".url":
        url = read_text_file(src).strip().splitlines()[0]
        page = _fetch_html(url)
        name, base = (urlparse(url).hostname or "page"), url
    else:
        page = read_text_file(src)
        name, base = safe_stem(src), None
    dest = unique_path(out, f"{name}.pdf")
    _render_html(page, dest, base)
    return [dest]


# ───────────────────────── TXT → PDF ─────────────────────────
def txt_to_pdf(files: list[Path], out: Path, p: Params) -> list[Path]:
    src = files[0]
    text = read_text_file(src)
    if not text.strip():
        raise ToolError("no_text")
    rtl = is_rtl_text(text)
    doc = f"""<!DOCTYPE html><html dir="{'rtl' if rtl else 'ltr'}"><head><meta charset="utf-8"><style>
@page{{size:A4;margin:2cm}}
body{{font-family:'Noto Naskh Arabic','Noto Sans Arabic','DejaVu Sans',Arial,sans-serif;font-size:12pt;line-height:1.7;white-space:pre-wrap;word-wrap:break-word;
text-align:{'right' if rtl else 'left'}}}
</style></head><body>{html.escape(text)}</body></html>"""
    dest = unique_path(out, f"{safe_stem(src)}.pdf")
    _render_html(doc, dest)
    return [dest]