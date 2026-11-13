"""End-to-end handler flow tests using fake Telegram objects (no network)."""
import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS

import pypdf
from reportlab.pdfgen import canvas

os.environ["TEMP_DIR"] = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")

from bot import handlers as h  # noqa: E402


class Chat:
    id = 1

    def __init__(self):
        self.texts, self.docs = [], []

    async def send_message(self, text, **kw):
        self.texts.append(text)
        return Msg(self)

    async def send_document(self, fh, filename=None, **kw):
        self.docs.append((filename, len(fh.read())))

    async def send_action(self, *a, **k):
        pass


class Msg:
    def __init__(self, chat, text=None, document=None, photo=None):
        self.chat, self.text, self.document, self.photo = chat, text, document, photo

    async def reply_text(self, text, **kw):
        self.chat.texts.append(text)

    async def delete(self):
        pass


class TgFile:
    def __init__(self, src):
        self.src = src

    async def get_file(self):
        return self

    async def download_to_drive(self, dest):
        shutil.copy(self.src, dest)


def doc(src: Path):
    d = TgFile(src)
    d.file_name, d.file_size, d.file_unique_id = src.name, src.stat().st_size, "uid"
    return d


class Query:
    def __init__(self, chat, data):
        self.data, self.chat = data, chat
        self.message = Msg(chat)

    async def answer(self):
        pass

    async def edit_message_text(self, text, **kw):
        self.chat.texts.append(text)


class Ctx:
    def __init__(self):
        self.user_data, self.tasks = {}, []
        self.bot = NS(send_chat_action=self._noop)
        self.application = NS(bot_data={}, create_task=self._task)

    async def _noop(self, *a, **k):
        pass

    def _task(self, coro, update=None):
        t = asyncio.ensure_future(coro)
        self.tasks.append(t)
        return t


def upd(chat, msg=None, query=None):
    return NS(effective_user=NS(id=7, first_name="Ali"), effective_chat=chat, effective_message=msg, callback_query=query)


def make_pdf(path: Path, pages=3):
    c = canvas.Canvas(str(path))
    for i in range(pages):
        c.drawString(72, 700, f"page {i + 1}")
        c.showPage()
    c.save()
    return path


async def press(ctx, chat, data):
    await h.on_callback(upd(chat, query=Query(chat, data)), ctx)


async def send_doc(ctx, chat, src):
    await h._receive_file(upd(chat, Msg(chat, document=doc(src))), ctx, doc(src), src.name, src.stat().st_size)


async def finish(ctx):
    await asyncio.gather(*ctx.tasks)


def test_merge_batch_flow(tmp_path=None):
    async def run():
        d = Path(tempfile.mkdtemp())
        a, b = make_pdf(d / "a.pdf", 2), make_pdf(d / "b.pdf", 3)
        chat, ctx = Chat(), Ctx()
        await press(ctx, chat, "tool:merge")
        await send_doc(ctx, chat, a)
        await press(ctx, chat, "done")  # only 1 file → refused
        assert any("2" in t for t in chat.texts[-1:])
        await send_doc(ctx, chat, b)
        await press(ctx, chat, "done")
        await finish(ctx)
        assert chat.docs and chat.docs[0][0] == "merged.pdf"
        assert "s" not in ctx.user_data  # session cleaned up
    asyncio.run(run())


def test_param_flow_and_retry():
    async def run():
        d = Path(tempfile.mkdtemp())
        f = make_pdf(d / "doc.pdf", 4)
        chat, ctx = Chat(), Ctx()
        await press(ctx, chat, "tool:extract_pages")
        await send_doc(ctx, chat, f)
        assert ctx.user_data["s"].stage == "params"
        await h.on_text(upd(chat, Msg(chat, text="99")), ctx)  # invalid → must re-ask, not abort
        await finish(ctx)
        assert not chat.docs and ctx.user_data["s"].stage == "params"
        ctx.tasks.clear()
        await h.on_text(upd(chat, Msg(chat, text="2-3")), ctx)
        await finish(ctx)
        name, size = chat.docs[-1]
        assert name.endswith("_extracted.pdf")
    asyncio.run(run())


def test_choice_params_and_zip_for_many_outputs():
    async def run():
        d = Path(tempfile.mkdtemp())
        f = make_pdf(d / "doc.pdf", 5)
        chat, ctx = Chat(), Ctx()
        await press(ctx, chat, "tool:rotate")
        await send_doc(ctx, chat, f)
        await press(ctx, chat, "p:90")
        await h.on_text(upd(chat, Msg(chat, text="all")), ctx)
        await finish(ctx)
        assert chat.docs[-1][0].endswith("_rotated.pdf")
        # split into 5 pages → >3 outputs → one ZIP
        chat2, ctx2 = Chat(), Ctx()
        await press(ctx2, chat2, "tool:split")
        await send_doc(ctx2, chat2, f)
        await h.on_text(upd(chat2, Msg(chat2, text="all")), ctx2)
        await finish(ctx2)
        assert len(chat2.docs) == 1 and chat2.docs[0][0].endswith(".zip")
    asyncio.run(run())


def test_smart_suggestions_and_wrong_ext():
    async def run():
        d = Path(tempfile.mkdtemp())
        f = make_pdf(d / "doc.pdf", 2)
        chat, ctx = Chat(), Ctx()
        await send_doc(ctx, chat, f)  # no tool chosen → suggestions
        assert ctx.user_data["s"].tool is None and ctx.user_data["s"].files
        await press(ctx, chat, "use:pdf2txt")
        await finish(ctx)
        assert chat.docs[-1][0].endswith(".txt")
        # wrong extension for the chosen tool
        chat3, ctx3 = Chat(), Ctx()
        await press(ctx3, chat3, "tool:jpg2png")
        await send_doc(ctx3, chat3, f)
        assert "pdf" in chat3.texts[-1] and not chat3.docs
    asyncio.run(run())


def test_text_input_txt2pdf():
    async def run():
        chat, ctx = Chat(), Ctx()
        await press(ctx, chat, "tool:txt2pdf")
        await h.on_text(upd(chat, Msg(chat, text="مرحبا\\nHello")), ctx)
        await finish(ctx)
        assert chat.docs[-1][0].endswith(".pdf")
    asyncio.run(run())


def test_ssrf_url_rejected():
    async def run():
        chat, ctx = Chat(), Ctx()
        await press(ctx, chat, "tool:html2pdf")
        await h.on_text(upd(chat, Msg(chat, text="http://169.254.169.254/latest/meta-data")), ctx)
        await finish(ctx)
        assert not chat.docs and any("🚫" in t for t in chat.texts)
    asyncio.run(run())
