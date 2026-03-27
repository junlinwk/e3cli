"""課程相關 API。"""

from __future__ import annotations

from e3cli.api.client import MoodleClient


def get_enrolled_courses(client: MoodleClient, userid: int) -> list[dict]:
    """取得使用者已註冊的課程列表。"""
    return client.call("core_enrol_get_users_courses", userid=userid)


def get_course_contents(client: MoodleClient, courseid: int) -> list[dict]:
    """
    取得課程內容（章節 → 模組 → 檔案）。

    回傳結構：
    [
      {
        "id": section_id, "name": "第一週", "modules": [
          {"id": mod_id, "modname": "resource", "name": "...",
           "contents": [{"filename": "...", "fileurl": "...", "filesize": ..., "timemodified": ...}]}
        ]
      }
    ]
    """
    return client.call("core_course_get_contents", courseid=courseid)
