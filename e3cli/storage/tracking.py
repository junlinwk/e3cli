"""追蹤邏輯的高階封裝。"""

from __future__ import annotations

from e3cli.storage.db import Database


def get_pending_assignments(db: Database) -> list:
    """取得尚未提交的作業。"""
    rows = db.get_assignments()
    return [r for r in rows if r["status"] not in ("submitted",) and r["duedate"] != 0]
