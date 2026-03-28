"""e3cli assignments"""

from __future__ import annotations

import time

import typer
from rich.console import Console
from rich.table import Table

from e3cli.api.assignments import get_assignments, get_submission_status_text
from e3cli.api.courses import get_enrolled_courses
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client, get_db
from e3cli.formatting import format_duedate, format_submission_status, sort_assignments
from e3cli.i18n import t
from e3cli.semester import filter_current_semester

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def assignments(
    due_soon: int = typer.Option(None, "--due-soon", help=t("assign.opt_due_soon")),
    all_semesters: bool = typer.Option(False, "--all", "-a", help="Show all semesters"),
):
    """List assignments and deadlines with submission status."""
    client = get_client()
    db = get_db()

    info = get_site_info(client)
    course_list = get_enrolled_courses(client, info["userid"])

    if not all_semesters:
        filtered = filter_current_semester(course_list)
        if filtered:
            course_list = filtered

    courseids = [c["id"] for c in course_list]
    course_names = {c["id"]: c.get("shortname", "") for c in course_list}

    if not courseids:
        console.print(f"[yellow]{t('common.no_courses')}[/yellow]")
        raise typer.Exit()

    data = get_assignments(client, courseids)
    now = int(time.time())

    # 收集所有作業 + 查詢狀態
    console.print(f"[dim]{t('assign.checking_status')}[/dim]")
    raw_items = []
    for course in data.get("courses", []):
        cid = course["id"]
        cname = course_names.get(cid, "")
        for a in course.get("assignments", []):
            duedate = a.get("duedate", 0)
            if due_soon is not None:
                if duedate == 0 or duedate - now > due_soon * 86400 or duedate < now:
                    continue
            status = get_submission_status_text(client, a["id"])
            db.upsert_assignment(a["id"], cid, cname, a["name"], duedate, now)
            db.update_assignment_status(a["id"], status)
            raw_items.append((a, status, cid, cname, duedate))

    if not raw_items:
        console.print(f"[green]{t('assign.empty')}[/green]")
        db.close()
        return

    # 排序
    sorted_items = sort_assignments(raw_items, now)

    table = Table(title=t("assign.title"))
    table.add_column(t("courses.col_id"), style="dim")
    table.add_column(t("assign.col_course"), style="cyan")
    table.add_column(t("assign.col_name"), style="bold")
    table.add_column(t("assign.col_due"))
    table.add_column(t("assign.col_status"))

    for a, status, cid, cname, duedate in sorted_items:
        table.add_row(
            str(a["id"]),
            cname,
            a["name"],
            format_duedate(duedate),
            format_submission_status(status),
        )

    console.print(table)
    db.close()
