"""SQLite 資料庫管理 — 追蹤已下載的檔案和作業狀態。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
    id          INTEGER PRIMARY KEY,
    shortname   TEXT NOT NULL,
    fullname    TEXT NOT NULL,
    last_synced INTEGER
);

CREATE TABLE IF NOT EXISTS downloaded_files (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id     INTEGER NOT NULL,
    module_id     INTEGER NOT NULL,
    filename      TEXT NOT NULL,
    fileurl       TEXT NOT NULL,
    filesize      INTEGER,
    time_modified INTEGER NOT NULL,
    local_path    TEXT NOT NULL,
    downloaded_at INTEGER NOT NULL,
    UNIQUE(course_id, module_id, filename)
);

CREATE TABLE IF NOT EXISTS assignments (
    id            INTEGER PRIMARY KEY,
    course_id     INTEGER NOT NULL,
    course_name   TEXT NOT NULL DEFAULT '',
    name          TEXT NOT NULL,
    duedate       INTEGER,
    status        TEXT DEFAULT 'new',
    last_checked  INTEGER,
    notified      INTEGER DEFAULT 0
);
"""


class Database:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # --- 課程 ---

    def upsert_course(self, course_id: int, shortname: str, fullname: str) -> None:
        self.conn.execute(
            "INSERT INTO courses (id, shortname, fullname) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET shortname=excluded.shortname, fullname=excluded.fullname",
            (course_id, shortname, fullname),
        )
        self.conn.commit()

    def get_courses(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM courses ORDER BY id").fetchall()

    # --- 已下載檔案 ---

    def is_downloaded(self, course_id: int, module_id: int, filename: str, time_modified: int) -> bool:
        """檢查檔案是否已下載且未更新。"""
        row = self.conn.execute(
            "SELECT time_modified FROM downloaded_files "
            "WHERE course_id=? AND module_id=? AND filename=?",
            (course_id, module_id, filename),
        ).fetchone()
        return row is not None and row["time_modified"] >= time_modified

    def record_download(
        self, course_id: int, module_id: int, filename: str,
        fileurl: str, filesize: int, time_modified: int,
        local_path: str, downloaded_at: int,
    ) -> None:
        self.conn.execute(
            "INSERT INTO downloaded_files "
            "(course_id, module_id, filename, fileurl, filesize, time_modified, local_path, downloaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(course_id, module_id, filename) DO UPDATE SET "
            "fileurl=excluded.fileurl, filesize=excluded.filesize, "
            "time_modified=excluded.time_modified, local_path=excluded.local_path, "
            "downloaded_at=excluded.downloaded_at",
            (course_id, module_id, filename, fileurl, filesize, time_modified, local_path, downloaded_at),
        )
        self.conn.commit()

    # --- 作業 ---

    def upsert_assignment(
        self, assign_id: int, course_id: int, course_name: str,
        name: str, duedate: int, last_checked: int,
    ) -> bool:
        """更新或新增作業，回傳是否為新作業。"""
        existing = self.conn.execute("SELECT id FROM assignments WHERE id=?", (assign_id,)).fetchone()
        self.conn.execute(
            "INSERT INTO assignments (id, course_id, course_name, name, duedate, last_checked) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "name=excluded.name, duedate=excluded.duedate, last_checked=excluded.last_checked",
            (assign_id, course_id, course_name, name, duedate, last_checked),
        )
        self.conn.commit()
        return existing is None

    def get_assignments(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM assignments ORDER BY duedate ASC"
        ).fetchall()

    def update_assignment_status(self, assign_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE assignments SET status=? WHERE id=?", (status, assign_id)
        )
        self.conn.commit()
