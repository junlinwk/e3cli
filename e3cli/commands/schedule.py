"""e3cli schedule — 管理定時同步排程。"""

from __future__ import annotations

import typer
from rich.console import Console

from e3cli.config import load_config
from e3cli.scheduler import cron

console = Console()
app = typer.Typer()


@app.command()
def enable(
    interval: int = typer.Option(None, "--interval", "-i", help="同步間隔 (分鐘)"),
):
    """啟用定時同步 (安裝 cron job)。"""
    cfg = load_config()
    minutes = interval or cfg.schedule.interval_minutes
    cron.install(minutes)
    console.print(f"[green]✓ 已啟用定時同步，每 {minutes} 分鐘執行一次。[/green]")


@app.command()
def disable():
    """停用定時同步 (移除 cron job)。"""
    cron.uninstall()
    console.print("[green]✓ 已停用定時同步。[/green]")


@app.command()
def status():
    """顯示目前排程狀態。"""
    if cron.is_installed():
        line = cron.get_schedule_line()
        console.print("[green]✓ 排程已啟用[/green]")
        console.print(f"  [dim]{line}[/dim]")
    else:
        console.print("[yellow]排程未啟用。使用 e3cli schedule enable 來啟用。[/yellow]")
