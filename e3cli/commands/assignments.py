"""e3cli assignments"""

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
from e3cli.i18n import t

console = Console()
app = typer.Typer()


def _format_duedate(ts: int) -> str:
    if ts == 0:
        return t("assign.no_deadline")
    dt = datetime.fromtimestamp(ts)
    remaining = ts - int(time.time())
    days = remaining // 86400
    if remaining < 0:
        return f"[red]{dt:%Y-%m-%d %H:%M} ({t('assign.expired')})[/red]"
    if days <= 3:
        return f"[red]{dt:%Y-%m-%d %H:%M} ({t('assign.days_left', n=days)})[/red]"
    if days <= 7:
        return f"[yellow]{dt:%Y-%m-%d %H:%M} ({t('assign.days_left', n=days)})[/yellow]"
    return f"{dt:%Y-%m-%d %H:%M} ({t('assign.days_left', n=days)})"


@app.callback(invoke_without_command=True)
def assignments(
    due_soon: int = typer.Option(None, "--due-soon", help=t("assign.opt_due_soon")),
):
    """List assignments and deadlines."""
    client = get_client()
    db = get_db()

    info = get_site_info(client)
    course_list = get_enrolled_courses(client, info["userid"])
    courseids = [c["id"] for c in course_list]
    course_names = {c["id"]: c.get("shortname", "") for c in course_list}

    if not courseids:
        console.print(f"[yellow]{t('common.no_courses')}[/yellow]")
        raise typer.Exit()

    data = get_assignments(client, courseids)
    now = int(time.time())

    table = Table(title=t("assign.title"))
    table.add_column(t("courses.col_id"), style="dim")
    table.add_column(t("assign.col_course"), style="cyan")
    table.add_column(t("assign.col_name"), style="bold")
    table.add_column(t("assign.col_due"))
    table.add_column(t("assign.col_status"))

    count = 0
    for course in data.get("courses", []):
        cid = course["id"]
        cname = course_names.get(cid, "")
        for a in course.get("assignments", []):
            duedate = a.get("duedate", 0)

            if due_soon is not None:
                if duedate == 0 or duedate - now > due_soon * 86400 or duedate < now:
                    continue

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
        console.print(f"[green]{t('assign.empty')}[/green]")
    else:
        console.print(table)

    db.close()
