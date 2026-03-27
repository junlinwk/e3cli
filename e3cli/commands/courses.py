"""e3cli courses"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from e3cli.api.courses import get_enrolled_courses
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client
from e3cli.i18n import t

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def courses():
    """List all enrolled courses."""
    client = get_client()
    info = get_site_info(client)
    userid = info["userid"]

    course_list = get_enrolled_courses(client, userid)

    if not course_list:
        console.print(f"[yellow]{t('courses.empty')}[/yellow]")
        raise typer.Exit()

    table = Table(title=f"{t('courses.title')} ({info['fullname']})")
    table.add_column(t("courses.col_id"), style="dim")
    table.add_column(t("courses.col_code"), style="cyan")
    table.add_column(t("courses.col_name"), style="bold")

    for c in course_list:
        table.add_row(str(c["id"]), c.get("shortname", ""), c.get("fullname", ""))

    console.print(table)
