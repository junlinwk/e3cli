"""
學期工具 — 解析課程代碼中的學期資訊，支援多校。

支援的學期格式（透過 config.toml 設定 semester_format）：
  "nycu"    — 前4碼：1142 = 114學年第2學期 (預設)
  "ntu"     — 前5碼：1132-  = 113學年第2學期
  "western" — 前4碼：2025 = 2025年
  "none"    — 不解析，所有課程視為當期
  自訂 regex — 使用者提供正規表達式

學年計算 (NYCU/台灣)：
  民國年 = 西元年 - 1911
  8月~隔年1月 = 第1學期
  2月~7月 = 第2學期
"""

from __future__ import annotations

import re
from datetime import date


# ─── Semester format presets ────────────────────────────────────────────

_PRESETS = {
    "nycu": {
        "pattern": r"^(\d{4})",
        "current_fn": "_current_nycu",
        "format_fn": "_format_nycu",
    },
    "ntu": {
        "pattern": r"^(\d{4})",
        "current_fn": "_current_nycu",  # same academic year system
        "format_fn": "_format_nycu",
    },
    "western": {
        "pattern": r"^(20\d{2})",
        "current_fn": "_current_western",
        "format_fn": "_format_western",
    },
    "none": {
        "pattern": None,
        "current_fn": None,
        "format_fn": None,
    },
}

_semester_format: str = "nycu"
_custom_pattern: str | None = None


def set_semester_format(fmt: str) -> None:
    """設定學期格式。可以是 preset 名稱或自訂 regex。"""
    global _semester_format, _custom_pattern
    if fmt in _PRESETS:
        _semester_format = fmt
        _custom_pattern = None
    else:
        _semester_format = "custom"
        _custom_pattern = fmt


def _current_nycu() -> str:
    """NYCU/台灣學制的當前學期代碼。"""
    today = date.today()
    year = today.year
    month = today.month
    if month >= 8:
        academic_year = year - 1911
        semester = 1
    elif month >= 2:
        academic_year = year - 1911 - 1
        semester = 2
    else:
        academic_year = year - 1911 - 1
        semester = 1
    return f"{academic_year}{semester}"


def _current_western() -> str:
    """西曆年制的當前代碼。"""
    return str(date.today().year)


def _format_nycu(code: str) -> str:
    """格式化台灣學期代碼。"""
    if len(code) != 4:
        return code
    return f"{code[:3]}學年第{code[3]}學期"


def _format_western(code: str) -> str:
    return code


# ─── Public API ─────────────────────────────────────────────────────────

def get_current_semester_code() -> str:
    """取得當前學期代碼。"""
    if _semester_format == "none":
        return ""
    preset = _PRESETS.get(_semester_format)
    if preset and preset["current_fn"]:
        fn = globals()[preset["current_fn"]]
        return fn()
    return _current_nycu()


def parse_semester_code(shortname: str) -> str | None:
    """從課程代碼提取學期代碼。"""
    if _semester_format == "none":
        return None
    preset = _PRESETS.get(_semester_format)
    pattern = _custom_pattern if _semester_format == "custom" else (preset["pattern"] if preset else None)
    if not pattern:
        return None
    match = re.match(pattern, shortname)
    return match.group(1) if match else None


def format_semester(code: str) -> str:
    """格式化學期代碼為可讀字串。"""
    if not code:
        return ""
    preset = _PRESETS.get(_semester_format)
    if preset and preset["format_fn"]:
        fn = globals()[preset["format_fn"]]
        return fn(code)
    return code


def is_current_semester(shortname: str) -> bool:
    if _semester_format == "none":
        return True
    code = parse_semester_code(shortname)
    if code is None:
        return False
    return code == get_current_semester_code()


def filter_current_semester(courses: list[dict]) -> list[dict]:
    """過濾只保留當期課程。semester_format=none 時回傳全部。"""
    if _semester_format == "none":
        return courses
    current = get_current_semester_code()
    if not current:
        return courses
    return [c for c in courses if parse_semester_code(c.get("shortname", "")) == current]


def group_by_semester(courses: list[dict]) -> dict[str, list[dict]]:
    """按學期分組課程，最新的在前。"""
    groups: dict[str, list[dict]] = {}
    for c in courses:
        code = parse_semester_code(c.get("shortname", "")) or "other"
        groups.setdefault(code, []).append(c)
    return dict(sorted(groups.items(), key=lambda x: x[0], reverse=True))


def fuzzy_match_course(courses: list[dict], query: str) -> list[dict]:
    """模糊匹配課程名稱或代碼。"""
    query_lower = query.lower()
    results = []
    for c in courses:
        shortname = c.get("shortname", "").lower()
        fullname = c.get("fullname", "").lower()
        if query_lower in shortname or query_lower in fullname:
            results.append(c)
            continue
        words = query_lower.split()
        combined = f"{shortname} {fullname}"
        if all(w in combined for w in words):
            results.append(c)
    return results
