"""Commands 共用工具。"""

from __future__ import annotations

import typer
from rich.console import Console

from e3cli.api.client import MoodleClient
from e3cli.config import load_config, load_token
from e3cli.storage.db import Database

console = Console()


def get_client() -> MoodleClient:
    """取得已認證的 MoodleClient，token 不存在則提示登入。"""
    cfg = load_config()
    token = load_token()
    if not token:
        console.print("[red]尚未登入，請先執行 e3cli login[/red]")
        raise typer.Exit(1)
    return MoodleClient(cfg.moodle.url, token)


def get_db() -> Database:
    """取得 SQLite Database 實例。"""
    cfg = load_config()
    return Database(cfg.storage.db_path)
