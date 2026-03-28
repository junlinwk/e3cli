"""作業相關 API。"""

from __future__ import annotations

from e3cli.api.client import MoodleClient


def get_assignments(client: MoodleClient, courseids: list[int]) -> dict:
    """
    取得指定課程的所有作業。

    回傳: {"courses": [{"id": ..., "assignments": [{...}]}]}
    """
    params = {f"courseids[{i}]": cid for i, cid in enumerate(courseids)}
    return client.call("mod_assign_get_assignments", **params)


def get_submission_status(client: MoodleClient, assignid: int) -> dict:
    """取得某作業的提交狀態。"""
    return client.call("mod_assign_get_submission_status", assignid=assignid)


def get_submission_status_text(client: MoodleClient, assignid: int) -> str:
    """
    取得作業提交狀態的文字描述。

    回傳: "submitted", "draft", "new", "reopened", 或 "unknown"
    """
    try:
        data = get_submission_status(client, assignid)
        return (
            data.get("lastattempt", {})
            .get("submission", {})
            .get("status", "new")
        )
    except Exception:
        return "unknown"


def save_submission(client: MoodleClient, assignid: int, draft_itemid: int, text: str = "") -> dict:
    """
    提交作業（檔案已上傳到 draft area 後）。

    draft_itemid: upload_file 回傳的 itemid
    text: 可選的線上文字內容
    """
    params = {
        "assignmentid": assignid,
        "plugindata[files_filemanager]": draft_itemid,
    }
    if text:
        params["plugindata[onlinetext_editor][text]"] = text
        params["plugindata[onlinetext_editor][format]"] = 1  # HTML
        params["plugindata[onlinetext_editor][itemid]"] = draft_itemid
    return client.call("mod_assign_save_submission", **params)
