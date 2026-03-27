"""e3cli courses — 列出修課清單。"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from e3cli.api.courses import get_enrolled_courses
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def courses():
    """列出目前註冊的所有課程。"""
    client = get_client()
    info = get_site_info(client)
    userid = info["userid"]

    course_list = get_enrolled_courses(client, userid)

    if not course_list:
        console.print("[yellow]找不到任何課程。[/yellow]")
        raise typer.Exit()

    table = Table(title=f"修課清單 ({info['fullname']})")
    table.add_column("ID", style="dim")
    table.add_column("課程代碼", style="cyan")
    table.add_column("課程名稱", style="bold")

    for c in course_list:
        table.add_row(str(c["id"]), c.get("shortname", ""), c.get("fullname", ""))

    console.print(table)
