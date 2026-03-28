"""e3cli courses — 按學期分組列出修課清單。"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from e3cli.api.courses import get_enrolled_courses
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client
from e3cli.i18n import t
from e3cli.semester import format_semester, get_current_semester_code, group_by_semester

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def courses(
    all_semesters: bool = typer.Option(False, "--all", "-a", help="Show all semesters"),
    semester: str = typer.Option(None, "--semester", help="Filter by semester code (e.g. 1142)"),
):
    """List enrolled courses (grouped by semester)."""
    client = get_client()
    info = get_site_info(client)
    userid = info["userid"]

    course_list = get_enrolled_courses(client, userid)

    if not course_list:
        console.print(f"[yellow]{t('courses.empty')}[/yellow]")
        raise typer.Exit()

    groups = group_by_semester(course_list)
    current = get_current_semester_code()

    # 過濾學期
    if semester:
        groups = {k: v for k, v in groups.items() if k == semester}
    elif not all_semesters:
        # 預設只顯示當期，如果當期沒有就顯示全部
        if current in groups:
            groups = {current: groups[current]}

    for sem_code, sem_courses in groups.items():
        is_current = sem_code == current
        sem_label = format_semester(sem_code) if sem_code != "other" else t("sem.other")
        marker = " ★" if is_current else ""

        table = Table(
            title=f"{sem_label}{marker}",
            title_style="bold green" if is_current else "bold",
        )
        table.add_column(t("courses.col_id"), style="dim", width=8)
        table.add_column(t("courses.col_code"), style="cyan")
        table.add_column(t("courses.col_name"), style="bold")

        for c in sem_courses:
            table.add_row(str(c["id"]), c.get("shortname", ""), c.get("fullname", ""))

        console.print(table)
        console.print()
