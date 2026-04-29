"""Parse NYCU E3 course names into (code, zh_name, en_name).

NYCU 的 fullname 通常是：
    <semester>.<course_id>.<中文名> <English Name>
例如：
    1142.430107.Go人工智慧大數據平行運算 Artificial intelligent big data parallel computation by Go

shortname 通常是 `<sem>.<id>`（或舊格式 `<sem>_<id>_<sec>`）。
"""

from __future__ import annotations

import re

from e3cli.i18n import get_lang

_PREFIX_RE = re.compile(r"^\d+[._\-]\d+(?:[._\-]\d+)?[._\-\s]+")
_CODE_RE = re.compile(r"^(\d+[._\-]\d+(?:[._\-]\d+)?)")


def _is_cjk(ch: str) -> bool:
    code = ord(ch)
    return (
        0x4E00 <= code <= 0x9FFF       # CJK Unified Ideographs
        or 0x3400 <= code <= 0x4DBF    # Extension A
        or 0xF900 <= code <= 0xFAFF    # Compatibility Ideographs
        or 0x3040 <= code <= 0x30FF    # Hiragana / Katakana
    )


def parse_course_name(fullname: str, shortname: str = "") -> tuple[str, str, str]:
    """Return (code, zh_name, en_name).

    - code 取自 shortname；若無則從 fullname 開頭抽出。
    - 砍掉 fullname 開頭的 `<sem>.<id>.` 前綴，剩下的依「最後一個 CJK 字 + 空白」切成
      中文/英文兩段。
    - 純中文或純英文都能正確處理。
    """
    fullname = fullname or ""
    shortname = shortname or ""

    rest = fullname
    if shortname and fullname.startswith(shortname):
        rest = fullname[len(shortname):].lstrip("._- ")
    else:
        m = _PREFIX_RE.match(fullname)
        if m:
            rest = fullname[m.end():]

    code = shortname
    if not code:
        m = _CODE_RE.match(fullname)
        if m:
            code = m.group(1)

    last_cjk = -1
    for i, ch in enumerate(rest):
        if _is_cjk(ch):
            last_cjk = i

    if last_cjk == -1:
        return code, "", rest.strip()

    after = rest[last_cjk + 1:]
    sm = re.match(r"^\s+(.*)$", after)
    if sm:
        return code, rest[:last_cjk + 1].strip(), sm.group(1).strip()
    return code, rest.strip(), ""


def display_name(fullname: str, shortname: str = "", lang: str | None = None) -> str:
    """純課名（不含課號），依使用者語言挑中文或英文。沒有對應語言時 fallback 另一語言。"""
    if lang is None:
        lang = get_lang()
    _, zh, en = parse_course_name(fullname, shortname)
    if lang == "zh":
        return zh or en or fullname
    return en or zh or fullname


def display_with_code(
    fullname: str,
    shortname: str = "",
    lang: str | None = None,
    bold_name: bool = True,
) -> str:
    """格式：`<code>  <name>`。bold_name=True 時 name 包 [bold] markup（給 rich 用）。"""
    code, zh, en = parse_course_name(fullname, shortname)
    if lang is None:
        lang = get_lang()
    name = (zh if lang == "zh" else en) or zh or en or ""
    if not code:
        return f"[bold]{name}[/bold]" if bold_name and name else name
    if not name:
        return code
    return f"{code}  [bold]{name}[/bold]" if bold_name else f"{code}  {name}"


def other_lang_name(fullname: str, shortname: str = "", lang: str | None = None) -> str:
    """另一個語言的課名（用於 TUI 描述行）。"""
    if lang is None:
        lang = get_lang()
    _, zh, en = parse_course_name(fullname, shortname)
    return en if lang == "zh" else zh


_FS_UNSAFE_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _sanitize_dirname(name: str) -> str:
    """清理檔案系統不允許的字元。"""
    cleaned = _FS_UNSAFE_RE.sub("_", name).strip().rstrip(".")
    return cleaned


def course_dir_name(
    fullname: str,
    shortname: str = "",
    lang: str | None = None,
    fallback: str = "",
) -> str:
    """課程下載目錄名 — sanitize 過的純課名（依使用者語言）。空時用 fallback。"""
    name = display_name(fullname, shortname, lang=lang)
    if not name:
        name = fallback or shortname
    sanitized = _sanitize_dirname(name)
    return sanitized or _sanitize_dirname(shortname) or _sanitize_dirname(fallback)


def migrate_course_dir(
    base_dir,
    fullname: str,
    shortname: str = "",
    lang: str | None = None,
) -> str:
    """若舊的 shortname 資料夾存在但新名資料夾不存在，rename。回傳新目錄名。"""
    new_name = course_dir_name(fullname, shortname, lang=lang)
    legacy_name = _sanitize_dirname(shortname) if shortname else ""
    if legacy_name and legacy_name != new_name:
        legacy_dir = base_dir / legacy_name
        new_dir = base_dir / new_name
        if legacy_dir.exists() and not new_dir.exists():
            try:
                legacy_dir.rename(new_dir)
            except OSError:
                pass
    return new_name
