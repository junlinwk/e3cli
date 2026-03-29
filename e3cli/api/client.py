"""Moodle REST API 客戶端。"""

from __future__ import annotations

from e3cli.http import get_session_for_url


class MoodleAPIError(Exception):
    """Moodle API 回傳錯誤。"""

    def __init__(self, errorcode: str, message: str):
        self.errorcode = errorcode
        super().__init__(f"[{errorcode}] {message}")


class MoodleClient:
    """封裝 Moodle Web Service REST API 呼叫。"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = get_session_for_url(self.base_url)
        self.rest_endpoint = f"{self.base_url}/webservice/rest/server.php"
        self.upload_endpoint = f"{self.base_url}/webservice/upload.php"

    def call(self, wsfunction: str, **kwargs) -> dict | list:
        """
        呼叫 Moodle Web Service 函式。

        所有參數以 POST form data 傳送，Moodle 使用 bracket notation
        處理巢狀參數（如 courseids[0]=123）。
        """
        params = {
            "wstoken": self.token,
            "wsfunction": wsfunction,
            "moodlewsrestformat": "json",
            **kwargs,
        }
        resp = self.session.post(self.rest_endpoint, data=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Moodle 錯誤格式: {"exception": ..., "errorcode": ..., "message": ...}
        if isinstance(data, dict) and "exception" in data:
            raise MoodleAPIError(data.get("errorcode", "unknown"), data.get("message", "未知錯誤"))

        return data

    def upload_file(self, filepath, itemid: int = 0) -> list[dict]:
        """
        上傳檔案到使用者的 draft area。

        回傳包含 itemid, filename 等資訊的 list。
        """
        from pathlib import Path
        filepath = Path(filepath)

        with open(filepath, "rb") as f:
            resp = self.session.post(
                self.upload_endpoint,
                params={"token": self.token},
                data={"itemid": itemid, "filepath": "/"},
                files={"file_1": (filepath.name, f)},
                timeout=120,
            )
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, dict) and "exception" in data:
            raise MoodleAPIError(data.get("errorcode", "unknown"), data.get("message", "上傳失敗"))

        return data

    def download_url(self, fileurl: str) -> str:
        """為檔案 URL 附加 token 參數以供下載。"""
        sep = "&" if "?" in fileurl else "?"
        return f"{fileurl}{sep}token={self.token}"
