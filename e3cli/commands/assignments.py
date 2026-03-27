"""e3cli assignments — 列出作業與截止日期。"""

from __future__ import annotations

import time
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from e3cli.api.assignments import get_assignments
from e3cli.api.courses import get_enrolled_courses
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client, get_db

console = Console()
app = typer.Typer()


def _format_duedate(ts: int) -> str:
    if ts == 0:
        return "無截止日"
    dt = datetime.fromtimestamp(ts)
    remaining = ts - int(time.time())
    if remaining < 0:
        return f"[red]{dt:%Y-%m-%d %H:%M} (已過期)[/red]"
    days = remaining // 86400
    if days <= 3:
        return f"[red]{dt:%Y-%m-%d %H:%M} ({days}天後)[/red]"
    if days <= 7:
        return f"[yellow]{dt:%Y-%m-%d %H:%M} ({days}天後)[/yellow]"
    return f"{dt:%Y-%m-%d %H:%M} ({days}天後)"


@app.callback(invoke_without_command=True)
def assignments(
    due_soon: int = typer.Option(None, "--due-soon", help="只顯示 N 天內到期的作業"),
):
    """列出所有作業與截止日期。"""
    client = get_client()
    db = get_db()

    info = get_site_info(client)
    course_list = get_enrolled_courses(client, info["userid"])
    courseids = [c["id"] for c in course_list]
    course_names = {c["id"]: c.get("shortname", "") for c in course_list}

    if not courseids:
        console.print("[yellow]沒有課程。[/yellow]")
        raise typer.Exit()

    data = get_assignments(client, courseids)
    now = int(time.time())

    table = Table(title="作業列表")
    table.add_column("ID", style="dim")
    table.add_column("課程", style="cyan")
    table.add_column("作業名稱", style="bold")
    table.add_column("截止日期")
    table.add_column("狀態")

    count = 0
    for course in data.get("courses", []):
        cid = course["id"]
        cname = course_names.get(cid, "")
        for a in course.get("assignments", []):
            duedate = a.get("duedate", 0)

            # 過濾 due_soon
            if due_soon is not None:
                if duedate == 0 or duedate - now > due_soon * 86400 or duedate < now:
                    continue

            # 更新資料庫
            db.upsert_assignment(a["id"], cid, cname, a["name"], duedate, now)

            table.add_row(
                str(a["id"]),
                cname,
                a["name"],
                _format_duedate(duedate),
                a.get("submissionstatus", "new") if "submissionstatus" in a else "—",
            )
            count += 1

    if count == 0:
        console.print("[green]沒有符合條件的作業。[/green]")
    else:
        console.print(table)

    db.close()
