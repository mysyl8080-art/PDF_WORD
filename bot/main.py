"""Entry point:  python -m bot.main"""
from __future__ import annotations

import logging
import sys

from telegram import BotCommand, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from . import handlers as h
from .config import settings


def build_app() -> Application:
    if not settings.bot_token or ":" not in settings.bot_token:
        sys.exit("❌ BOT_TOKEN is missing. Copy .env.example to .env and set your token from @BotFather.")
    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    builder = Application.builder().token(settings.bot_token).concurrent_updates(True).post_init(_post_init)
    if settings.local_api_url:  # Local Bot API server → files up to 2 GB
        builder = (
            builder.base_url(f"{settings.local_api_url}/bot")
            .base_file_url(f"{settings.local_api_url}/file/bot")
            .local_mode(True)
        )
    app = builder.build()

    app.add_handler(CommandHandler("start", h.cmd_start))
    app.add_handler(CommandHandler("menu", h.cmd_menu))
    app.add_handler(CommandHandler("help", h.cmd_help))
    app.add_handler(CommandHandler("cancel", h.cmd_cancel))
    app.add_handler(CommandHandler("lang", h.cmd_lang))
    app.add_handler(CommandHandler("stats", h.cmd_stats))
    app.add_handler(CallbackQueryHandler(h.on_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, h.on_document))
    app.add_handler(MessageHandler(filters.PHOTO, h.on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, h.on_text))
    app.add_error_handler(h.on_error)
    app.job_queue.run_repeating(h.cleanup_job, interval=1800, first=60)
    return app


async def _post_init(app: Application) -> None:
    await app.bot.set_my_commands(
        [
            BotCommand("start", "القائمة الرئيسية / Main menu"),
            BotCommand("menu", "الأدوات / Tools"),
            BotCommand("cancel", "إلغاء / Cancel"),
            BotCommand("lang", "اللغة / Language"),
            BotCommand("help", "مساعدة / Help"),
        ]
    )


def main() -> None:
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    build_app().run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()