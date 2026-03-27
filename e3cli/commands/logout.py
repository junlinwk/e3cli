"""e3cli logout — 清除所有認證資料。"""

from __future__ import annotations

import typer
from rich.console import Console

from e3cli.credential import clear_credentials

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def logout():
    """清除已儲存的 token 與帳密。"""
    clear_credentials()
    console.print("[green]✓ 所有認證資料已安全清除。[/green]")
