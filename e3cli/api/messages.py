"""站內訊息 API。"""

from __future__ import annotations

from e3cli.api.client import MoodleClient


def send_message(client: MoodleClient, to_userid: int, text: str) -> list[dict]:
    """
    發送站內訊息給指定使用者。

    對方會依通知設定決定是否收到 email。
    回傳: [{"msgid": int, "text": str, "errormessage": str}]
    """
    return client.call(
        "core_message_send_instant_messages",
        **{
            "messages[0][touserid]": to_userid,
            "messages[0][text]": text,
        },
    )


def get_conversations(client: MoodleClient, userid: int) -> dict:
    """取得使用者的對話列表。"""
    return client.call(
        "core_message_get_conversations",
        userid=userid,
        type=1,  # 1=private messages
        limitnum=20,
    )
