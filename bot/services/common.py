"""Shared helpers for all services."""
from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pypdf

from ..config import settings


class ToolError(Exception):
    """User-facing error. `code` maps to i18n key `err_<code>`."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def safe_stem(path: Path | str) -> str:
    stem = Path(path).stem
    stem = re.sub(r"[^\w\-. \u0600-\u06FF]", "_", stem, flags=re.UNICODE).strip(" ._")
    return (stem or "file")[:80]


def unique_path(directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / name
    i = 1
    while p.exists():
        p = directory / f"{Path(name).stem}_{i}{Path(name).suffix}"
        i += 1
    return p


def ext_of(path: Path | str) -> str:
    return Path(path).suffix.lower().lstrip(".")


def open_reader(path: Path, password: str | None = None) -> pypdf.PdfReader:
    try:
        reader = pypdf.PdfReader(str(path))
        if reader.is_encrypted:
            if reader.decrypt(password or "") == 0:
                raise ToolError("encrypted")
        _ = len(reader.pages)  # force parse
        return reader
    except ToolError:
        raise
    except Exception as e:  # corrupted / not a pdf
        raise ToolError("bad_pdf", str(e)) from e


def check_pages(total: int, limit: int) -> None:
    if total > limit:
        raise ToolError("too_many_pages", f"{total}>{limit}")


def parse_ranges(spec: str, total: int, *, allow_all: bool = True, dedupe: bool = False) -> list[int]:
    """Parse '1-3,5,7-' → zero-based page indexes (order preserved).

    Accepts Arabic-Indic digits, Arabic comma, 'all'/'الكل'.
    """
    s = (spec or "").strip().translate(_AR_DIGITS).replace("،", ",").replace("؛", ",").replace(";", ",")
    s = s.replace("–", "-").replace("—", "-").replace("إلى", "-").replace(" ", "")
    if allow_all and s.lower() in {"all", "*", "الكل", "كل"}:
        return list(range(total))
    if not s:
        raise ToolError("bad_pages", spec)
    out: list[int] = []
    for part in s.split(","):
        if not part:
            continue
        m = re.fullmatch(r"(\d*)-(\d*)", part)
        if m:
            a = int(m.group(1)) if m.group(1) else 1
            b = int(m.group(2)) if m.group(2) else total
            if a > b:
                a, b = b, a
            rng = range(a, b + 1)
        elif part.isdigit():
            rng = range(int(part), int(part) + 1)
        else:
            raise ToolError("bad_pages", part)
        for n in rng:
            if n < 1 or n > total:
                raise ToolError("bad_pages", f"{n} / {total}")
            out.append(n - 1)
    if not out:
        raise ToolError("bad_pages", spec)
    if dedupe:
        seen: set[int] = set()
        out = [x for x in out if not (x in seen or seen.add(x))]
    return out


def make_zip(files: list[Path], dest: Path) -> Path:
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, arcname=f.name)
    return dest


def run_cmd(cmd: list[str], timeout: int = 180, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env, check=False)
    except subprocess.TimeoutExpired as e:
        raise ToolError("timeout") from e
    except FileNotFoundError as e:
        raise ToolError("unsupported", f"missing binary: {cmd[0]}") from e


def has_binary(name: str) -> bool:
    return shutil.which(name) is not None


def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1256", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def is_rtl_text(text: str) -> bool:
    ar = sum(1 for c in text if "\u0600" <= c <= "\u06FF" or "\u0750" <= c <= "\u077F")
    lat = sum(1 for c in text if c.isascii() and c.isalpha())
    return ar > lat


def cap_pages(total: int) -> None:
    check_pages(total, settings.max_pdf_pages)