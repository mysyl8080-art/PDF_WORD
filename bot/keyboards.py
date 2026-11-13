from __future__ import annotations

from telegram import InlineKeyboardButton as B
from telegram import InlineKeyboardMarkup as M

from .i18n import t
from .registry import CATEGORIES, ParamSpec, Tool, tools_in

PAGE_SIZE = 8


def main_menu(lang: str) -> M:
    rows, row = [], []
    for key, icon, ar, en in CATEGORIES:
        row.append(B(f"{icon} {ar if lang == 'ar' else en}", callback_data=f"cat:{key}:0"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([B(t(lang, "btn_lang"), callback_data="lang")])
    return M(rows)


def category_menu(lang: str, cat: str, page: int = 0) -> M:
    tools = tools_in(cat)
    chunk = tools[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    rows = [[B(f"{x.icon} {x.name(lang)}", callback_data=f"tool:{x.key}")] for x in chunk]
    nav = []
    if page > 0:
        nav.append(B("◀️", callback_data=f"cat:{cat}:{page - 1}"))
    if (page + 1) * PAGE_SIZE < len(tools):
        nav.append(B("▶️", callback_data=f"cat:{cat}:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([B(t(lang, "btn_back"), callback_data="menu")])
    return M(rows)


def collecting(lang: str, n: int) -> M:
    rows = []
    if n:
        rows.append([B(t(lang, "btn_done", n=n), callback_data="done")])
    rows.append([B(t(lang, "btn_cancel"), callback_data="cancel")])
    return M(rows)


def cancel_only(lang: str) -> M:
    return M([[B(t(lang, "btn_cancel"), callback_data="cancel")]])


def param_choices(lang: str, spec: ParamSpec) -> M:
    rows = [[B(ar if lang == "ar" else en, callback_data=f"p:{val}")] for val, ar, en in spec.choices]
    rows.append([B(t(lang, "btn_cancel"), callback_data="cancel")])
    return M(rows)


def suggestions(lang: str, tools: list[Tool]) -> M:
    rows = [[B(f"{x.icon} {x.name(lang)}", callback_data=f"use:{x.key}")] for x in tools[:10]]
    rows.append([B(t(lang, "btn_cancel"), callback_data="cancel")])
    return M(rows)


def after_job(lang: str) -> M:
    return M([[B(t(lang, "btn_menu"), callback_data="menu")]])