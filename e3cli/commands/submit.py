"""e3cli submit — 提交作業。"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from e3cli.api.assignments import get_submission_status, save_submission
from e3cli.commands._common import get_client, get_db

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def submit(
    assignment_id: int = typer.Argument(..., help="作業 ID"),
    files: list[Path] = typer.Argument(..., help="要提交的檔案路徑"),
    text: str = typer.Option("", "--text", "-t", help="線上文字內容 (可選)"),
    force: bool = typer.Option(False, "--force", "-f", help="強制提交（即使已過截止日）"),
):
    """上傳檔案並提交作業。"""
    # 驗證檔案存在
    for f in files:
        if not f.exists():
            console.print(f"[red]✗ 檔案不存在: {f}[/red]")
            raise typer.Exit(1)

    client = get_client()
    db = get_db()

    # 檢查作業狀態
    console.print(f"[dim]檢查作業 #{assignment_id} 狀態...[/dim]")
    try:
        status = get_submission_status(client, assignment_id)
    except Exception as e:
        console.print(f"[red]✗ 無法取得作業資訊: {e}[/red]")
        raise typer.Exit(1)

    # 檢查截止日
    assign_info = status.get("lastattempt", {}).get("assign", {})
    duedate = assign_info.get("duedate", 0)
    if duedate and duedate < int(time.time()) and not force:
        dt = datetime.fromtimestamp(duedate)
        console.print(f"[red]✗ 作業已於 {dt:%Y-%m-%d %H:%M} 截止。使用 --force 可強制提交。[/red]")
        raise typer.Exit(1)

    # 上傳檔案
    console.print(f"[dim]上傳 {len(files)} 個檔案...[/dim]")
    itemid = 0
    for f in files:
        result = client.upload_file(f, itemid=itemid)
        if result and isinstance(result, list):
            itemid = result[0].get("itemid", itemid)
        console.print(f"  ✓ {f.name}")

    # 提交
    console.print("[dim]提交作業中...[/dim]")
    save_submission(client, assignment_id, itemid, text)

    # 驗證
    verify = get_submission_status(client, assignment_id)
    sub_status = (
        verify.get("lastattempt", {})
        .get("submission", {})
        .get("status", "unknown")
    )

    if sub_status == "submitted":
        console.print("[green]✓ 作業提交成功！[/green]")
        db.update_assignment_status(assignment_id, "submitted")
    elif sub_status == "draft":
        console.print("[yellow]⚠ 作業已儲存為草稿，可能需要到 Moodle 手動確認提交。[/yellow]")
        db.update_assignment_status(assignment_id, "draft")
    else:
        console.print(f"[yellow]⚠ 提交狀態: {sub_status}[/yellow]")

    db.close()
