"""課程相關 API。"""

from __future__ import annotations

from e3cli.api.client import MoodleClient


def get_enrolled_courses(client: MoodleClient, userid: int) -> list[dict]:
    """取得使用者已註冊的課程列表。"""
    return client.call("core_enrol_get_users_courses", userid=userid)


def get_course_contents(client: MoodleClient, courseid: int) -> list[dict]:
    """取得課程內容（章節 → 模組 → 檔案）。"""
    return client.call("core_course_get_contents", courseid=courseid)


def get_grades(client: MoodleClient, courseid: int, userid: int) -> dict:
    """取得課程成績。"""
    return client.call("gradereport_user_get_grade_items", courseid=courseid, userid=userid)
