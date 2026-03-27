"""站點資訊 API。"""

from __future__ import annotations

from e3cli.api.client import MoodleClient


def get_site_info(client: MoodleClient) -> dict:
    """取得站點資訊，包含 userid、username、sitename 等。"""
    return client.call("core_webservice_get_site_info")
