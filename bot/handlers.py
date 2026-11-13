"""Telegram handlers: menus, file collection, parameter prompts, job execution."""
from __future__ import annotations

import asyncio
import html
import logging
import shutil
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from telegram import Message, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from . import keyboards as kb
from .config import settings
from .db import db
from .i18n import t
from .registry import CATEGORIES, TOOL_MAP, Tool, tools_for_ext
from .services.common import ToolError, ext_of, make_zip, safe_stem

log = logging.getLogger("toolsbot")
POOL = ThreadPoolExecutor(max_workers=settings.workers, thread_name_prefix="job")
MAX_INDIVIDUAL_FILES = 3  # more outputs than this are sent as a single ZIP
RETRY_CODES = {"bad_pages", "reorder", "weak_password"}  # re-ask the last parameter instead of aborting


# ───────────────────────── session ─────────────────────────
@dataclass
class Session:
    tool: Tool | None = None
    files: list[Path] = field(default_factory=list)
    params: dict = field(default_factory=dict)
    param_idx: int = 0
    stage: str = "files"  # files | params | running
    workdir: Path | None = None

    @property
    def indir(self) -> Path:
        assert self.workdir
        return self.workdir / "in"

    @property
    def outdir(self) -> Path:
        assert self.workdir
        return self.workdir / "out"


def _lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = context.user_data.get("lang")
    if not lang and update.effective_user:
        lang = db.touch_user(update.effective_user.id, settings.default_lang)
        context.user_data["lang"] = lang
    return lang or settings.default_lang


def _lock(context: ContextTypes.DEFAULT_TYPE) -> asyncio.Lock:
    return context.user_data.setdefault("lock", asyncio.Lock())


def _session(context: ContextTypes.DEFAULT_TYPE) -> Session | None:
    return context.user_data.get("s")


def _new_session(context: ContextTypes.DEFAULT_TYPE, user_id: int, tool: Tool | None) -> Session:
    _reset(context)
    s = Session(tool=tool, workdir=settings.temp_dir / f"{user_id}_{uuid.uuid4().hex[:10]}")
    s.indir.mkdir(parents=True, exist_ok=True)
    s.outdir.mkdir(parents=True, exist_ok=True)
    context.user_data["s"] = s
    return s


def _reset(context: ContextTypes.DEFAULT_TYPE) -> None:
    s: Session | None = context.user_data.pop("s", None)
    if s and s.stage == "running":  # never delete files under a running job
        context.user_data["s"] = s
        return
    if s and s.workdir:
        shutil.rmtree(s.workdir, ignore_errors=True)


def _formats(tool: Tool) -> str:
    return ", ".join(tool.accepts)


def _esc(s: str) -> str:
    return html.escape(s, quote=False)


async def _edit_or_send(update: Update, text: str, markup=None) -> None:
    q = update.callback_query
    if q and q.message:
        try:
            await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
            return
        except BadRequest as e:
            if "not modified" in str(e).lower():
                return
        except TelegramError:
            pass
    if update.effective_chat:
        await update.effective_chat.send_message(text, parse_mode=ParseMode.HTML, reply_markup=markup)


# ───────────────────────── commands ─────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with _lock(context):
        _reset(context)
        lang = _lang(update, context)
        name = _esc(update.effective_user.first_name or "")
        await update.effective_message.reply_text(
            t(lang, "welcome", name=name), parse_mode=ParseMode.HTML, reply_markup=kb.main_menu(lang)
        )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with _lock(context):
        _reset(context)
        lang = _lang(update, context)
        await update.effective_message.reply_text(
            t(lang, "menu_title"), parse_mode=ParseMode.HTML, reply_markup=kb.main_menu(lang)
        )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(update, context)
    await update.effective_message.reply_text(t(lang, "help"), parse_mode=ParseMode.HTML, reply_markup=kb.after_job(lang))


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with _lock(context):
        lang = _lang(update, context)
        s = _session(context)
        if s and s.stage == "running":
            await update.effective_message.reply_text(t(lang, "busy"))
            return
        _reset(context)
        await update.effective_message.reply_text(t(lang, "cancelled"), reply_markup=kb.after_job(lang))


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _toggle_lang(update, context, from_callback=False)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(update, context)
    if update.effective_user.id not in settings.admin_ids:
        await update.effective_message.reply_text(t(lang, "admin_only"))
        return
    st = db.stats()
    top = "\n".join(f"• {TOOL_MAP[k].name(lang) if k in TOOL_MAP else k}: {n}" for k, n in st["top"]) or "—"
    await update.effective_message.reply_text(t(lang, "stats", **{**st, "top": top}), parse_mode=ParseMode.HTML)


async def _toggle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback: bool) -> None:
    new = "en" if _lang(update, context) == "ar" else "ar"
    context.user_data["lang"] = new
    db.set_lang(update.effective_user.id, new)
    text = t(new, "lang_set") + "\n\n" + t(new, "menu_title")
    if from_callback:
        await _edit_or_send(update, text, kb.main_menu(new))
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb.main_menu(new))


# ───────────────────────── callbacks ─────────────────────────
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    async with _lock(context):
        lang = _lang(update, context)
        s = _session(context)
        uid = update.effective_user.id

        if data == "menu":
            if s and s.stage == "running":
                return
            _reset(context)
            await _edit_or_send(update, t(lang, "menu_title"), kb.main_menu(lang))

        elif data == "lang":
            await _toggle_lang(update, context, from_callback=True)

        elif data.startswith("cat:"):
            _, cat, page = data.split(":")
            icon, ar, en = next((i, a, e) for k, i, a, e in CATEGORIES if k == cat)
            await _edit_or_send(
                update, t(lang, "cat_title", icon=icon, name=ar if lang == "ar" else en),
                kb.category_menu(lang, cat, int(page)),
            )

        elif data.startswith("tool:"):
            tool = TOOL_MAP.get(data[5:])
            if not tool or (s and s.stage == "running"):
                return
            s = _new_session(context, uid, tool)
            await _prompt_for_files(update, lang, tool, s)

        elif data.startswith("use:"):  # chosen from smart suggestions (file already uploaded)
            tool = TOOL_MAP.get(data[4:])
            if not tool or not s or s.stage == "running" or not s.files:
                return
            s.tool = tool
            if not all(ext_of(f) in tool.accepts for f in s.files):
                await _edit_or_send(update, t(lang, "wrong_ext", ext=ext_of(s.files[0]), formats=_formats(tool)))
                return
            if tool.batch:
                await _edit_or_send(
                    update, t(lang, "file_added", fname=_esc(s.files[-1].name), n=len(s.files)),
                    kb.collecting(lang, len(s.files)),
                )
            else:
                await _after_files(update, context, s, lang)

        elif data == "done":
            if not s or not s.tool or s.stage != "files":
                return
            if len(s.files) < s.tool.min_files:
                await q.message.reply_text(t(lang, "need_files", n=s.tool.min_files))
                return
            await _after_files(update, context, s, lang)

        elif data == "cancel":
            if s and s.stage == "running":
                await q.message.reply_text(t(lang, "busy"))
                return
            _reset(context)
            await _edit_or_send(update, t(lang, "cancelled"), kb.after_job(lang))

        elif data.startswith("p:"):
            if not s or not s.tool or s.stage != "params":
                return
            spec = s.tool.params[s.param_idx]
            if spec.choices and data[2:] in {c[0] for c in spec.choices}:
                await _store_param(update, context, s, lang, data[2:])


async def _prompt_for_files(update: Update, lang: str, tool: Tool, s: Session) -> None:
    if tool.batch:
        text = t(lang, "tool_send_many", icon=tool.icon, name=tool.name(lang), formats=_formats(tool),
                 limit=settings.max_files_per_job, max=settings.max_file_mb)
        if tool.min_files > 1:
            text += t(lang, "min_files_hint", n=tool.min_files)
    else:
        text = t(lang, "tool_send_one", icon=tool.icon, name=tool.name(lang), formats=_formats(tool), max=settings.max_file_mb)
    if tool.allow_text:
        text += t(lang, "tool_send_or_text")
    await _edit_or_send(update, text, kb.cancel_only(lang))


# ───────────────────────── incoming files ─────────────────────────
async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.effective_message.document
    await _receive_file(update, context, doc, doc.file_name or f"file_{doc.file_unique_id}", doc.file_size or 0)


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.effective_message.photo[-1]
    await _receive_file(update, context, photo, f"photo_{photo.file_unique_id}.jpg", photo.file_size or 0)


async def _receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE, tg_obj, fname: str, size: int) -> None:
    msg = update.effective_message
    async with _lock(context):  # keeps batch uploads in the exact order the user sent them
        lang = _lang(update, context)
        s = _session(context)
        if s and s.stage in ("running", "params"):
            await msg.reply_text(t(lang, "busy") if s.stage == "running" else t(lang, "ask_text_btn"))
            return
        ext = ext_of(fname)
        if size > settings.max_file_mb * 1024 * 1024:
            await msg.reply_text(t(lang, "too_big", size=size / 1048576, max=settings.max_file_mb))
            return

        if not s or not s.tool:  # smart mode: no tool picked yet
            suggestions = tools_for_ext(ext)
            if not suggestions:
                await msg.reply_text(t(lang, "no_suggest", ext=_esc(ext or "?")), parse_mode=ParseMode.HTML)
                return
            s = _new_session(context, update.effective_user.id, None)
        else:
            tool = s.tool
            if ext not in tool.accepts:
                await msg.reply_text(t(lang, "wrong_ext", ext=_esc(ext or "?"), formats=_formats(tool)), parse_mode=ParseMode.HTML)
                return
            if tool.batch and len(s.files) >= settings.max_files_per_job:
                await msg.reply_text(t(lang, "too_many_files", limit=settings.max_files_per_job), parse_mode=ParseMode.HTML)
                return

        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_DOCUMENT)
        dest = s.indir / f"{len(s.files):03d}_{safe_stem(fname)}.{ext or 'bin'}"
        try:
            f = await tg_obj.get_file()
            await f.download_to_drive(dest)
        except BadRequest as e:
            key = "too_big" if "too big" in str(e).lower() else "download_failed"
            await msg.reply_text(t(lang, key, size=size / 1048576, max=settings.max_file_mb))
            return
        except TelegramError:
            log.exception("download failed")
            await msg.reply_text(t(lang, "download_failed"))
            return

        if not s.tool:  # smart suggestions: keep only the latest file
            s.files = [dest]
            await msg.reply_text(
                t(lang, "suggest", fname=_esc(dest.name.split("_", 1)[-1])), parse_mode=ParseMode.HTML,
                reply_markup=kb.suggestions(lang, tools_for_ext(ext)),
            )
            return

        if s.tool.batch:
            s.files.append(dest)
            await msg.reply_text(
                t(lang, "file_added", fname=_esc(fname), n=len(s.files)), parse_mode=ParseMode.HTML,
                reply_markup=kb.collecting(lang, len(s.files)),
            )
        else:
            s.files = [dest]
            await _after_files(update, context, s, lang)


# ───────────────────────── text messages (params / text input) ─────────────────────────
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    text = (msg.text or "").strip()
    async with _lock(context):
        lang = _lang(update, context)
        s = _session(context)

        if s and s.tool and s.stage == "params":
            spec = s.tool.params[s.param_idx]
            if spec.choices:
                await msg.reply_text(t(lang, "ask_text_btn"))
                return
            if spec.sensitive:
                try:
                    await msg.delete()
                except TelegramError:
                    pass
            if not text or len(text) > 500:
                await msg.reply_text(t(lang, "param_bad"))
                return
            await _store_param(update, context, s, lang, text)
            return

        if s and s.tool and s.stage == "files" and s.tool.allow_text:
            ext = s.tool.allow_text
            if s.tool.key == "html2pdf" and text.lower().startswith(("http://", "https://")):
                ext = "url"
            dest = s.indir / f"{len(s.files):03d}_input.{ext}"
            dest.write_text(text, encoding="utf-8")
            s.files = [dest]
            await _after_files(update, context, s, lang)
            return

        if s and s.stage == "running":
            await msg.reply_text(t(lang, "busy"))
            return
        await msg.reply_text(t(lang, "no_session"), reply_markup=kb.main_menu(lang))


# ───────────────────────── flow ─────────────────────────
async def _after_files(update: Update, context: ContextTypes.DEFAULT_TYPE, s: Session, lang: str) -> None:
    assert s.tool
    if s.tool.params:
        s.stage, s.param_idx, s.params = "params", 0, {}
        await _ask_param(update, lang, s)
    else:
        await _start_job(update, context, s, lang)


async def _ask_param(update: Update, lang: str, s: Session) -> None:
    spec = s.tool.params[s.param_idx]
    prompt = spec.prompt_ar if lang == "ar" else spec.prompt_en
    markup = kb.param_choices(lang, spec) if spec.choices else kb.cancel_only(lang)
    chat = update.effective_chat
    await chat.send_message(prompt, parse_mode=ParseMode.HTML, reply_markup=markup)


async def _store_param(update: Update, context: ContextTypes.DEFAULT_TYPE, s: Session, lang: str, value: str) -> None:
    spec = s.tool.params[s.param_idx]
    s.params[spec.key] = value
    s.param_idx += 1
    if s.param_idx < len(s.tool.params):
        await _ask_param(update, lang, s)
    else:
        await _start_job(update, context, s, lang)


async def _start_job(update: Update, context: ContextTypes.DEFAULT_TYPE, s: Session, lang: str) -> None:
    busy: set[int] = context.application.bot_data.setdefault("busy", set())
    uid = update.effective_user.id
    if uid in busy:
        await update.effective_chat.send_message(t(lang, "busy"))
        return
    busy.add(uid)
    s.stage = "running"
    status = await update.effective_chat.send_message(t(lang, "processing"))
    context.application.create_task(_run_job(update, context, s, lang, status, uid), update=update)


async def _run_job(update: Update, context: ContextTypes.DEFAULT_TYPE, s: Session, lang: str, status: Message, uid: int) -> None:
    tool, chat = s.tool, update.effective_chat
    busy: set[int] = context.application.bot_data["busy"]
    started = time.monotonic()
    ok, retry_param = False, False
    try:
        shutil.rmtree(s.outdir, ignore_errors=True)
        s.outdir.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_running_loop()
        await chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        results: list[Path] = await asyncio.wait_for(
            loop.run_in_executor(POOL, tool.func, list(s.files), s.outdir, dict(s.params)),
            timeout=settings.job_timeout + 60,
        )
        await _send_results(chat, results, s, lang)
        ok = True
        await chat.send_message(t(lang, "done") + "\n" + t(lang, "done_more"), reply_markup=kb.after_job(lang))
    except ToolError as e:
        log.info("ToolError %s in %s: %s", e.code, tool.key, e.detail)
        await chat.send_message(t(lang, f"err_{e.code}", detail=_esc(e.detail)), parse_mode=ParseMode.HTML)
        retry_param = e.code in RETRY_CODES and bool(tool.params)
    except asyncio.TimeoutError:
        await chat.send_message(t(lang, "err_timeout"))
    except TelegramError:
        log.exception("send failed")
        await chat.send_message(t(lang, "send_failed"))
    except Exception:
        log.exception("job crashed: %s", tool.key)
        await chat.send_message(t(lang, "err_generic"))
    finally:
        busy.discard(uid)
        db.log_usage(uid, tool.key, ok, time.monotonic() - started)
        try:
            await status.delete()
        except TelegramError:
            pass
        async with _lock(context):
            if retry_param:  # let the user fix the bad value without re-uploading
                s.stage, s.param_idx = "params", len(tool.params) - 1
                s.params.pop(tool.params[-1].key, None)
                await _ask_param(update, lang, s)
            else:
                s.stage = "files"
                _reset(context)


async def _send_results(chat, results: list[Path], s: Session, lang: str) -> None:
    results = [r for r in results if r.exists()]
    if not results:
        raise ToolError("convert_failed", "no output")
    if len(results) > MAX_INDIVIDUAL_FILES:
        zip_path = make_zip(results, s.outdir / f"{safe_stem(results[0].stem.rsplit('_', 1)[0])}_{len(results)}files.zip")
        results = [zip_path]
    for r in results:
        with open(r, "rb") as fh:
            await chat.send_document(fh, filename=r.name, read_timeout=180, write_timeout=180, connect_timeout=30)


# ───────────────────────── housekeeping / errors ─────────────────────────
async def cleanup_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove orphaned work dirs (crashes, abandoned sessions) older than 1 hour."""
    root = settings.temp_dir
    if not root.exists():
        return
    now = time.time()
    for d in root.iterdir():
        try:
            if d.is_dir() and now - d.stat().st_mtime > 3600:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Unhandled exception", exc_info=context.error)