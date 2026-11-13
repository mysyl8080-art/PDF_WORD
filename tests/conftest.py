import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Offline sandboxes without python-telegram-bot / python-dotenv: install tiny stand-ins so the
# handler logic can still be exercised end-to-end. With real dependencies installed this is a no-op.
try:
    import telegram  # noqa: F401
except ImportError:
    class _Btn:
        def __init__(self, text, callback_data=None, **kw):
            self.text, self.callback_data = text, callback_data

    class _Markup:
        def __init__(self, rows):
            self.inline_keyboard = rows

    class _Err(Exception):
        pass

    class _BadRequest(_Err):
        pass

    tg = types.ModuleType("telegram")
    tg.InlineKeyboardButton, tg.InlineKeyboardMarkup = _Btn, _Markup
    tg.Message = tg.Update = object
    tg.BotCommand = lambda *a, **k: None
    const = types.ModuleType("telegram.constants")
    const.ChatAction = types.SimpleNamespace(UPLOAD_DOCUMENT="upload_document")
    const.ParseMode = types.SimpleNamespace(HTML="HTML")
    err = types.ModuleType("telegram.error")
    err.TelegramError, err.BadRequest = _Err, _BadRequest
    ext = types.ModuleType("telegram.ext")
    ext.ContextTypes = types.SimpleNamespace(DEFAULT_TYPE=object)
    for n in ("Application", "CallbackQueryHandler", "CommandHandler", "MessageHandler"):
        setattr(ext, n, object)
    ext.filters = types.SimpleNamespace()
    sys.modules.update({"telegram": tg, "telegram.constants": const, "telegram.error": err, "telegram.ext": ext})

try:
    import dotenv  # noqa: F401
except ImportError:
    d = types.ModuleType("dotenv")
    d.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = d
