"""課程成員 API。"""

from __future__ import annotations

from e3cli.api.client import MoodleClient


def get_enrolled_users(client: MoodleClient, courseid: int) -> list[dict]:
    """
    取得課程所有成員。

    回傳 list of:
    {
        "id": int,
        "fullname": str,
        "email": str,
        "roles": [{"roleid": int, "name": str, "shortname": str}],
        "profileimageurl": str,
        ...
    }
    """
    return client.call("core_enrol_get_enrolled_users", courseid=courseid)
