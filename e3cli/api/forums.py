"""論壇/公告 API。"""

from __future__ import annotations

from e3cli.api.client import MoodleClient


def get_forums(client: MoodleClient, courseids: list[int]) -> list[dict]:
    """
    取得課程的所有論壇。

    公告論壇的 type 通常是 "news"。
    回傳: [{"id": int, "course": int, "type": str, "name": str, ...}]
    """
    params = {f"courseids[{i}]": cid for i, cid in enumerate(courseids)}
    return client.call("mod_forum_get_forums_by_courses", **params)


def get_forum_discussions(client: MoodleClient, forumid: int, page: int = 0, perpage: int = 10) -> dict:
    """
    取得論壇的討論串（公告）。

    回傳:
    {
        "discussions": [
            {
                "id": int,
                "name": str,       # 標題
                "message": str,    # HTML 內容
                "timemodified": int,
                "userfullname": str,
                "attachments": [...],
                ...
            }
        ]
    }
    """
    return client.call(
        "mod_forum_get_forum_discussions",
        forumid=forumid,
        page=page,
        perpage=perpage,
        sortorder=-1,  # 最新的在前
    )
