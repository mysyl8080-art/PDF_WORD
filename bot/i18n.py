"""Arabic / English strings. Parse mode is HTML everywhere."""
from __future__ import annotations

T: dict[str, dict[str, str]] = {
    "ar": {
        "welcome": (
            "👋 أهلًا <b>{name}</b>!\n\n"
            "أنا بوت <b>أدوات الملفات الشامل</b> 🧰\n"
            "أحوّل وأعدّل وأحمي ملفات PDF والصور وأعمل OCR — كله من هنا بدون تثبيت أي برنامج.\n\n"
            "اختر قسمًا من الأسفل، أو <b>أرسل ملفك مباشرة</b> وسأقترح عليك الأدوات المناسبة له ✨"
        ),
        "menu_title": "🧰 <b>القائمة الرئيسية</b>\nاختر القسم:",
        "cat_title": "{icon} <b>{name}</b>\nاختر الأداة:",
        "tool_send_one": "{icon} <b>{name}</b>\n\n📎 أرسل الملف الآن.\n<i>الصيغ المدعومة:</i> <code>{formats}</code>\n<i>الحد الأقصى:</i> {max} MB",
        "tool_send_many": "{icon} <b>{name}</b>\n\n📎 أرسل الملفات واحدًا تلو الآخر (حتى {limit} ملف)، ثم اضغط <b>✅ تم</b>.\n<i>الصيغ المدعومة:</i> <code>{formats}</code>\n<i>الحد الأقصى للملف:</i> {max} MB",
        "tool_send_or_text": "\n\n✍️ أو أرسل النص / الرابط مباشرة كرسالة.",
        "min_files_hint": "\n<i>الحد الأدنى: {n} ملفات.</i>",
        "file_added": "✅ تمت إضافة <b>{fname}</b> — لديك الآن <b>{n}</b> ملف.\nأرسل المزيد أو اضغط <b>تم</b>.",
        "btn_done": "✅ تم ({n})",
        "btn_cancel": "❌ إلغاء",
        "btn_back": "⬅️ رجوع",
        "btn_menu": "🏠 القائمة",
        "btn_lang": "🌐 English",
        "processing": "⏳ جارٍ المعالجة… قد يستغرق بعض الوقت للملفات الكبيرة.",
        "queued": "⏳ طلبك في قائمة الانتظار…",
        "done": "✅ تم بنجاح! 🎉",
        "done_more": "ماذا تريد أن تفعل بعد ذلك؟",
        "cancelled": "تم الإلغاء. 👌",
        "no_session": "اختر أداة أولًا من القائمة 👇",
        "suggest": "📎 استلمت <b>{fname}</b>\nماذا تريد أن تفعل به؟",
        "no_suggest": "😕 لا توجد أدوات تدعم هذه الصيغة (<code>{ext}</code>). جرّب ملف PDF أو صورة أو مستند Office.",
        "wrong_ext": "⚠️ هذه الأداة لا تدعم صيغة <code>{ext}</code>.\nالصيغ المدعومة: <code>{formats}</code>",
        "too_big": "⚠️ حجم الملف ({size:.1f} MB) أكبر من الحد المسموح ({max} MB).",
        "too_many_files": "⚠️ وصلت للحد الأقصى ({limit} ملف). اضغط <b>تم</b> للمتابعة.",
        "need_files": "⚠️ أحتاج على الأقل {n} ملفات لهذه الأداة.",
        "busy": "⏳ لديك عملية قيد التنفيذ بالفعل. انتظر حتى تنتهي.",
        "download_failed": "⚠️ تعذر تنزيل الملف من تليجرام. حاول مرة أخرى.",
        "send_failed": "⚠️ تعذر إرسال النتيجة. حاول مرة أخرى.",
        "ask_text_btn": "اختر من الأزرار 👇",
        "param_bad": "⚠️ قيمة غير صالحة، أعد المحاولة.",
        "help": (
            "ℹ️ <b>طريقة الاستخدام</b>\n"
            "1️⃣ اختر أداة من القائمة (أو أرسل ملفك مباشرة)\n"
            "2️⃣ أرسل الملف (أو عدة ملفات ثم <b>تم</b>)\n"
            "3️⃣ أجب عن أي سؤال بسيط (مثل أرقام الصفحات)\n"
            "4️⃣ استلم النتيجة 🎁\n\n"
            "<b>الأوامر</b>\n/start — القائمة\n/menu — القائمة\n/cancel — إلغاء العملية الحالية\n/lang — تغيير اللغة\n/help — المساعدة\n\n"
            "🔒 <i>ملفاتك تُحذف من الخادم فور انتهاء المعالجة.</i>"
        ),
        "lang_set": "✅ تم تغيير اللغة إلى العربية.",
        "stats": (
            "📊 <b>الإحصائيات</b>\n👥 المستخدمون: {users}\n🟢 نشطون (24س): {active24}\n"
            "⚙️ العمليات: {jobs} (ناجحة {ok})\n🕒 آخر 24 ساعة: {jobs24}\n\n<b>الأكثر استخدامًا:</b>\n{top}"
        ),
        "admin_only": "هذا الأمر للأدمن فقط.",
        "cat_pdf_from": "تحويل من PDF", "cat_to_pdf": "تحويل إلى PDF", "cat_pdf_edit": "تعديل PDF",
        "cat_pdf_sec": "حماية PDF", "cat_pdf_extract": "استخراج و OCR", "cat_image": "تحويل الصور",
        # ── errors
        "err_encrypted": "🔐 الملف محمي بكلمة مرور. استخدم أداة <b>إزالة كلمة المرور</b> أولًا.",
        "err_bad_pdf": "⚠️ الملف تالف أو ليس PDF صالحًا.",
        "err_bad_pages": "⚠️ أرقام الصفحات غير صحيحة. مثال صحيح: <code>1-3,5,8-</code>\n<i>{detail}</i>",
        "err_reorder": "⚠️ يجب كتابة <b>كل</b> أرقام الصفحات (وعددها {detail}) مرة واحدة بالترتيب الجديد.",
        "err_scanned": "📷 هذا الملف يبدو <b>ممسوحًا ضوئيًا</b> (لا يحتوي نصًا). استخدم أداة <b>OCR</b> أولًا.",
        "err_no_images": "🤷 لم أجد صورًا داخل هذا الملف.",
        "err_no_text": "🤷 لم أتمكن من قراءة أي نص.",
        "err_wrong_password": "❌ كلمة المرور غير صحيحة.",
        "err_weak_password": "⚠️ كلمة المرور قصيرة جدًا (4 أحرف على الأقل).",
        "err_too_many_pages": "⚠️ عدد الصفحات كبير جدًا لهذه العملية ({detail}).",
        "err_convert_failed": "⚠️ فشل التحويل. تأكد أن الملف سليم وجرّب مرة أخرى.",
        "err_bad_image": "⚠️ تعذّرت قراءة الصورة — قد تكون تالفة.",
        "err_url_blocked": "🚫 هذا الرابط غير مسموح به (يجب أن يكون رابط http/https عامًّا).",
        "err_timeout": "⏱ استغرقت العملية وقتًا طويلًا وتم إيقافها. جرّب ملفًا أصغر.",
        "err_unsupported": "⚠️ هذه الميزة غير متوفرة حاليًا على الخادم.",
        "err_need_more_files": "⚠️ أحتاج ملفين على الأقل للدمج.",
        "err_generic": "😵 حدث خطأ غير متوقع. تم تسجيله، جرّب مرة أخرى لاحقًا.",
    },
    "en": {
        "welcome": (
            "👋 Hi <b>{name}</b>!\n\n"
            "I'm the <b>All-in-One File Tools</b> bot 🧰\n"
            "Convert, edit and protect PDFs & images, and run OCR — right here, nothing to install.\n\n"
            "Pick a category below, or <b>just send me a file</b> and I'll suggest the right tools ✨"
        ),
        "menu_title": "🧰 <b>Main menu</b>\nChoose a category:",
        "cat_title": "{icon} <b>{name}</b>\nChoose a tool:",
        "tool_send_one": "{icon} <b>{name}</b>\n\n📎 Send the file now.\n<i>Supported:</i> <code>{formats}</code>\n<i>Max size:</i> {max} MB",
        "tool_send_many": "{icon} <b>{name}</b>\n\n📎 Send files one by one (up to {limit}), then press <b>✅ Done</b>.\n<i>Supported:</i> <code>{formats}</code>\n<i>Max per file:</i> {max} MB",
        "tool_send_or_text": "\n\n✍️ Or just send text / a link as a message.",
        "min_files_hint": "\n<i>Minimum: {n} files.</i>",
        "file_added": "✅ Added <b>{fname}</b> — you now have <b>{n}</b> file(s).\nSend more or press <b>Done</b>.",
        "btn_done": "✅ Done ({n})",
        "btn_cancel": "❌ Cancel",
        "btn_back": "⬅️ Back",
        "btn_menu": "🏠 Menu",
        "btn_lang": "🌐 العربية",
        "processing": "⏳ Processing… large files may take a while.",
        "queued": "⏳ Your job is queued…",
        "done": "✅ Done! 🎉",
        "done_more": "What would you like to do next?",
        "cancelled": "Cancelled. 👌",
        "no_session": "Pick a tool from the menu first 👇",
        "suggest": "📎 Got <b>{fname}</b>\nWhat would you like to do with it?",
        "no_suggest": "😕 No tool supports this format (<code>{ext}</code>). Try a PDF, image or Office document.",
        "wrong_ext": "⚠️ This tool doesn't support <code>{ext}</code>.\nSupported: <code>{formats}</code>",
        "too_big": "⚠️ File size ({size:.1f} MB) exceeds the limit ({max} MB).",
        "too_many_files": "⚠️ Limit reached ({limit} files). Press <b>Done</b> to continue.",
        "need_files": "⚠️ I need at least {n} files for this tool.",
        "busy": "⏳ You already have a job running. Please wait for it to finish.",
        "download_failed": "⚠️ Couldn't download the file from Telegram. Please retry.",
        "send_failed": "⚠️ Couldn't send the result. Please retry.",
        "ask_text_btn": "Pick from the buttons 👇",
        "param_bad": "⚠️ Invalid value, please try again.",
        "help": (
            "ℹ️ <b>How it works</b>\n"
            "1️⃣ Pick a tool (or just send a file)\n"
            "2️⃣ Send the file (or several, then <b>Done</b>)\n"
            "3️⃣ Answer any quick question (e.g. page numbers)\n"
            "4️⃣ Get your result 🎁\n\n"
            "<b>Commands</b>\n/start — menu\n/menu — menu\n/cancel — cancel current job\n/lang — switch language\n/help — help\n\n"
            "🔒 <i>Your files are deleted from the server right after processing.</i>"
        ),
        "lang_set": "✅ Language switched to English.",
        "stats": (
            "📊 <b>Stats</b>\n👥 Users: {users}\n🟢 Active (24h): {active24}\n"
            "⚙️ Jobs: {jobs} (ok {ok})\n🕒 Last 24h: {jobs24}\n\n<b>Top tools:</b>\n{top}"
        ),
        "admin_only": "Admins only.",
        "cat_pdf_from": "Convert from PDF", "cat_to_pdf": "Convert to PDF", "cat_pdf_edit": "Edit PDF",
        "cat_pdf_sec": "PDF Security", "cat_pdf_extract": "Extract & OCR", "cat_image": "Image Tools",
        "err_encrypted": "🔐 This file is password-protected. Use <b>Remove password</b> first.",
        "err_bad_pdf": "⚠️ The file is corrupted or not a valid PDF.",
        "err_bad_pages": "⚠️ Invalid page numbers. Valid example: <code>1-3,5,8-</code>\n<i>{detail}</i>",
        "err_reorder": "⚠️ You must list <b>all</b> {detail} pages exactly once in the new order.",
        "err_scanned": "📷 This file looks <b>scanned</b> (no text layer). Use the <b>OCR</b> tool first.",
        "err_no_images": "🤷 No images found inside this file.",
        "err_no_text": "🤷 I couldn't read any text.",
        "err_wrong_password": "❌ Wrong password.",
        "err_weak_password": "⚠️ Password too short (min 4 characters).",
        "err_too_many_pages": "⚠️ Too many pages for this operation ({detail}).",
        "err_convert_failed": "⚠️ Conversion failed. Make sure the file is valid and retry.",
        "err_bad_image": "⚠️ Couldn't read the image — it may be corrupted.",
        "err_url_blocked": "🚫 This URL is not allowed (must be a public http/https link).",
        "err_timeout": "⏱ The job took too long and was stopped. Try a smaller file.",
        "err_unsupported": "⚠️ This feature isn't available on the server right now.",
        "err_need_more_files": "⚠️ I need at least 2 files to merge.",
        "err_generic": "😵 Unexpected error. It was logged — please try again later.",
    },
}


def t(lang: str, key: str, **kw) -> str:
    table = T.get(lang) or T["ar"]
    s = table.get(key) or T["en"].get(key) or key
    return s.format(**kw) if kw else s