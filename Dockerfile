FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DEBIAN_FRONTEND=noninteractive

# LibreOffice (Word/Excel/PowerPoint → PDF), Tesseract (OCR ar+en), WeasyPrint libs, Arabic-capable fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
      libreoffice-writer libreoffice-calc libreoffice-impress \
      tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
      fonts-noto-core fonts-dejavu-core fonts-hosny-amiri fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY bot ./bot
COPY tests ./tests

RUN useradd -m botuser && mkdir -p /app/data /tmp/toolsbot && chown -R botuser /app /tmp/toolsbot
USER botuser
ENV HOME=/home/botuser

CMD ["python", "-m", "bot.main"]
