"""
學期工具 — 解析課程代碼中的學期資訊，過濾當期課程。

NYCU 課程代碼格式：前4碼為學期代碼
  1142 = 114學年第2學期 (2026年2月~7月)
  1141 = 114學年第1學期 (2025年8月~2026年1月)

學年計算：民國年 = 西元年 - 1911
  8月~隔年1月 = 第1學期
  2月~7月 = 第2學期
"""

from __future__ import annotations

import re
from datetime import date


def get_current_semester_code() -> str:
    """計算當前學期代碼，例如 '1142'。"""
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


def parse_semester_code(shortname: str) -> str | None:
    """從課程代碼提取學期代碼，例如 '1142CS_OS' → '1142'。"""
    match = re.match(r"^(\d{4})", shortname)
    return match.group(1) if match else None


def format_semester(code: str) -> str:
    """格式化學期代碼為可讀字串，例如 '1142' → '114學年第2學期'。"""
    if len(code) != 4:
        return code
    year = code[:3]
    sem = code[3]
    return f"{year}學年第{sem}學期"


def is_current_semester(shortname: str) -> bool:
    """判斷課程是否屬於當前學期。"""
    code = parse_semester_code(shortname)
    if code is None:
        return False
    return code == get_current_semester_code()


def filter_current_semester(courses: list[dict]) -> list[dict]:
    """過濾只保留當期課程。"""
    current = get_current_semester_code()
    return [c for c in courses if parse_semester_code(c.get("shortname", "")) == current]


def group_by_semester(courses: list[dict]) -> dict[str, list[dict]]:
    """按學期分組課程，回傳 {semester_code: [courses]}，按學期倒序排列。"""
    groups: dict[str, list[dict]] = {}
    for c in courses:
        code = parse_semester_code(c.get("shortname", "")) or "other"
        groups.setdefault(code, []).append(c)
    # 按學期倒序（最新的在前）
    return dict(sorted(groups.items(), key=lambda x: x[0], reverse=True))


def fuzzy_match_course(courses: list[dict], query: str) -> list[dict]:
    """模糊匹配課程名稱或代碼。"""
    query_lower = query.lower()
    results = []
    for c in courses:
        shortname = c.get("shortname", "").lower()
        fullname = c.get("fullname", "").lower()
        # 精確子字串匹配
        if query_lower in shortname or query_lower in fullname:
            results.append(c)
            continue
        # 分詞模糊匹配：query 的每個詞都要出現
        words = query_lower.split()
        combined = f"{shortname} {fullname}"
        if all(w in combined for w in words):
            results.append(c)
    return results
