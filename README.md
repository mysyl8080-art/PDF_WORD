# 🧰 All-in-One Tools Bot — بوت تليجرام لأدوات الملفات الشامل

بوت تليجرام احترافي لتحويل وتعديل وحماية ملفات **PDF** والصور، مع **OCR** عربي/إنجليزي — كله من داخل المحادثة بدون تثبيت أي برنامج.
(واجهة عربية / إنجليزية، قوائم أزرار، معالجة متزامنة، حذف تلقائي للملفات بعد المعالجة).

## ✅ الأدوات المتوفرة (35 أداة)

| القسم | الأدوات |
|---|---|
| **تحويل من PDF** | PDF→JPG · PDF→PNG · PDF→Word · PDF→Excel · PDF→PowerPoint · PDF→TXT · PDF→HTML · PDF→EPUB |
| **تحويل إلى PDF** | JPG/PNG→PDF (عدة صور في ملف واحد) · Word→PDF · Excel→PDF · PowerPoint→PDF · TXT→PDF (أو نص مباشر) · HTML/رابط→PDF |
| **تعديل PDF** | دمج · تقسيم (صفحات منفصلة أو نطاقات) · استخراج صفحات · حذف صفحات · تدوير · إعادة ترتيب · أرقام الصفحات · Watermark (يدعم العربية) |
| **حماية PDF** | حماية بكلمة مرور (AES-256) · إزالة كلمة المرور (للملفات التي تملك كلمة مرورها) |
| **استخراج و OCR** | استخراج الصور · استخراج النصوص (مع اختيار الصفحات) · OCR للـ PDF الممسوح والصور ← ينتج PDF قابل للبحث + TXT + DOCX قابل للتعديل |
| **الصور** | JPG→PNG · PNG→JPG · WEBP→JPG · WEBP→PNG · JPG/PNG→WEBP · HEIC/BMP/GIF/TIFF→JPG · ضغط الصور · تغيير الحجم |

**تجربة المستخدم:** أرسل ملفك مباشرة وسيقترح البوت الأدوات المناسبة له تلقائيًا ✨ — أو اختر الأداة من القائمة. الأدوات الدفعية (دمج/صور) تجمع عدة ملفات ثم زر **تم**. لو أخطأت في أرقام الصفحات يطلب منك البوت القيمة مرة أخرى دون إعادة رفع الملف.

## 🚀 التشغيل السريع (Docker — الأسهل والموصى به)

```bash
# 1) أنشئ بوتًا من @BotFather وانسخ التوكن
cp .env.example .env          # ثم ضع BOT_TOKEN داخل .env
docker compose up -d --build  # يثبّت LibreOffice + Tesseract(عربي) + الخطوط تلقائيًا
docker compose logs -f
```

**بدون Docker (Linux/macOS):** ثبّت `libreoffice` و`tesseract-ocr tesseract-ocr-ara` ومكتبات WeasyPrint (pango)، ثم `./run_local.sh`.

## ⚙️ الإعدادات (`.env`)

| المتغير | الوصف | الافتراضي |
|---|---|---|
| `BOT_TOKEN` | توكن البوت (إجباري) | — |
| `ADMIN_IDS` | معرفات الأدمن لأمر `/stats` | — |
| `DEFAULT_LANG` | `ar` أو `en` | `ar` |
| `MAX_FILE_MB` | أقصى حجم ملف (20 على Cloud API) | 20 |
| `MAX_FILES_PER_JOB` / `MAX_PDF_PAGES` / `OCR_MAX_PAGES` | حدود الأمان | 30 / 300 / 40 |
| `OCR_LANGS` | لغات Tesseract | `ara+eng` |
| `WORKERS` | عدد العمليات الثقيلة المتزامنة | 3 |
| `ALLOW_URL_FETCH` | السماح بتحويل روابط الويب | true |
| `LOCAL_API_URL` | عنوان Local Bot API لرفع ملفات حتى 2GB | — |

> **ملفات أكبر من 20MB:** تليجرام (Cloud API) يسمح للبوت بتنزيل 20MB فقط. شغّل Local Bot API Server:
> `docker compose --profile local-api up -d` وضع `TELEGRAM_API_ID/HASH` و`LOCAL_API_URL` و`MAX_FILE_MB=2000`.

## 🗂 هيكل المشروع

```
bot/
  main.py          نقطة التشغيل وتسجيل الـ handlers
  handlers.py      القوائم، استقبال الملفات، الأسئلة، تنفيذ المهام، الإرسال
  registry.py      ⭐ تعريف كل الأدوات (مصدر الحقيقة الوحيد)
  keyboards.py     أزرار الإنلاين        i18n.py  النصوص عربي/إنجليزي
  db.py            SQLite (المستخدمون + الإحصائيات)       config.py  الإعدادات
  services/
    pdf_convert.py  PDF → صور/Word/Excel/PPT/TXT/HTML/EPUB
    to_pdf.py       صور/Office/TXT/HTML → PDF (+ حماية SSRF)
    pdf_edit.py     دمج/تقسيم/حذف/تدوير/ترتيب/ترقيم/Watermark
    pdf_security.py حماية وفك كلمة المرور
    pdf_extract.py  استخراج الصور والنصوص
    ocr.py          OCR عربي/إنجليزي
    image_tools.py  تحويل وضغط وتغيير حجم الصور
tests/             22 اختبارًا (خدمات + مسارات المحادثة الكاملة)
```

## ➕ إضافة أداة جديدة (3 خطوات)

1. اكتب دالة في `bot/services/` بالشكل: `def my_tool(files: list[Path], out: Path, params: dict) -> list[Path]` وارفع `ToolError("code")` للأخطاء المفهومة.
2. أضف سطر `Tool(...)` في `bot/registry.py` (الأسئلة/الأزرار تُعرَّف عبر `ParamSpec`).
3. (اختياري) أضف نص الخطأ `err_code` في `bot/i18n.py`.

القوائم والتحقق من الصيغ وجمع الملفات والإرسال (ZIP تلقائي لأكثر من 3 ملفات) كلها تعمل تلقائيًا.

## 🧪 الاختبارات

```bash
pip install -r requirements.txt && pytest -q
```

## 🔒 الأمان والخصوصية

- الملفات تُعالج في مجلد مؤقت لكل عملية وتُحذف فور الانتهاء، وتنظيف دوري لأي بقايا (كل 30 دقيقة).
- رسائل كلمات المرور تُحذف من المحادثة فور قراءتها.
- **إزالة كلمة المرور** تعمل فقط إن كنت تعرف كلمة المرور (أو كان الملف مقيّدًا بالتعديل/الطباعة فقط) — لا يوجد كسر للحماية.
- تحويل الروابط محمي من SSRF: يُرفض localhost والشبكات الداخلية وروابط `file://` ويُعاد فحص كل إعادة توجيه.
- حدود لحجم الملف وعدد الصفحات وزمن التنفيذ (`JOB_TIMEOUT_SEC`) لمنع إساءة الاستخدام.

## ⚠️ ملاحظات مهمة

- **PDF→Word** يعطي أفضل جودة مع الملفات الرقمية عبر `pdf2docx`؛ للملفات الممسوحة ضوئيًا استخدم **OCR** أولًا (يخبرك البوت بذلك تلقائيًا). مكتبة `pdf2docx` ترخيصها GPL وتعتمد على PyMuPDF (AGPL) — إن كان هذا لا يناسب مشروعك التجاري احذفها من `requirements.txt` وسيعمل الـ fallback النصي تلقائيًا، أو راجع ترخيص بديل.
- **PDF→PowerPoint** ينتج شريحة لكل صفحة بجودة عالية (الصفحة كصورة) مع النص المستخرج في ملاحظات الشريحة؛ **PDF→Excel** يستخرج الجداول كلٌّ في ورقة.
- **PDF→EPUB/HTML** نصيّان (بدون الحفاظ على التنسيق البصري).
- التحويلات الدقيقة لملفات Office تعتمد على LibreOffice (قد تختلف قليلًا عن Microsoft Office في الخطوط/التنسيقات المعقدة).
- تم اختبار الخدمات والـ flow كاملًا في بيئة معزولة؛ التشغيل الفعلي مع تليجرام يحتاج توكن البوت وإنترنت (لم يكن متاحًا أثناء الاختبار).

## 🗺 اقتراحات للتطوير القادم

Watermark بصورة · ضغط PDF · إزالة الخلفية للصور · تحويل الفيديو/الصوت · لوحة تحكم ويب · حدود يومية/اشتراكات · تشغيل بـ Webhook · طابور مهام (Redis/Celery) للتوسع.

---
# English summary
A production-ready Telegram bot: 35 tools — PDF↔JPG/PNG/DOCX/XLSX/PPTX/TXT/HTML/EPUB, Word/Excel/PPT/TXT/HTML→PDF, merge/split/extract/delete/rotate/reorder pages, page numbers, watermark, AES-256 protect/unlock, extract images/text, Arabic+English OCR, and image converters. Run `docker compose up -d --build` after setting `BOT_TOKEN` in `.env`.
