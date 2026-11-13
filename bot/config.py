"""Central configuration, loaded from environment variables / .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool(v: str | None, default: bool) -> bool:
    if not v:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _env(name: str, default: str = "") -> str:
    """Read env var and strip trailing inline comments."""
    return os.getenv(name, default).split("#")[0].strip()


def _ints(v: str) -> list[int]:
    return [int(p) for p in (x.strip() for x in v.split(",")) if p.isdigit()]


@dataclass(frozen=True)
class Config:
    bot_token: str = field(default_factory=lambda: _env("BOT_TOKEN"))
    admin_ids: list[int] = field(default_factory=lambda: _ints(_env("ADMIN_IDS")))
    default_lang: str = field(default_factory=lambda: _env("DEFAULT_LANG", "ar") or "ar")
    max_file_mb: int = field(default_factory=lambda: int(_env("MAX_FILE_MB", "20")))
    max_files_per_job: int = field(default_factory=lambda: int(_env("MAX_FILES_PER_JOB", "30")))
    max_pdf_pages: int = field(default_factory=lambda: int(_env("MAX_PDF_PAGES", "300")))
    ocr_max_pages: int = field(default_factory=lambda: int(_env("OCR_MAX_PAGES", "40")))
    ocr_langs: str = field(default_factory=lambda: _env("OCR_LANGS", "ara+eng"))
    workers: int = field(default_factory=lambda: int(_env("WORKERS", "3")))
    job_timeout: int = field(default_factory=lambda: int(_env("JOB_TIMEOUT_SEC", "300")))
    temp_dir: Path = field(default_factory=lambda: Path(_env("TEMP_DIR", "/tmp/toolsbot")))
    db_path: Path = field(default_factory=lambda: Path(_env("DB_PATH", "data/bot.db")))
    allow_url_fetch: bool = field(default_factory=lambda: _bool(_env("ALLOW_URL_FETCH"), True))
    local_api_url: str = field(default_factory=lambda: _env("LOCAL_API_URL"))


settings = Config()