"""檔案下載功能。"""

from __future__ import annotations

from pathlib import Path

from e3cli.api.client import MoodleClient


def download_file(client: MoodleClient, fileurl: str, dest: Path) -> Path:
    """
    從 Moodle 下載檔案到本地路徑。

    自動建立目標目錄，串流下載大檔案。
    """
    url = client.download_url(fileurl)
    resp = client.session.get(url, stream=True, timeout=120)
    resp.raise_for_status()

    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return dest
