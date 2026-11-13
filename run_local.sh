#!/usr/bin/env bash
# تشغيل محلي بدون Docker (Linux/macOS). يحتاج: python3.11+, libreoffice, tesseract-ocr(+ara), weasyprint deps.
set -e
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
[ -f .env ] || { cp .env.example .env; echo "✏️  عدّل ملف .env وضع BOT_TOKEN ثم شغّل السكربت مرة أخرى"; exit 0; }
python -m bot.main
