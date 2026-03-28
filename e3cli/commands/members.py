"""e3cli members — 列出課程成員。"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from e3cli.api.courses import get_enrolled_courses
from e3cli.api.members import get_enrolled_users
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client
from e3cli.i18n import t
from e3cli.semester import fuzzy_match_course

console = Console()
app = typer.Typer()


def _role_name(roles: list[dict]) -> str:
    """從 roles 列表取得角色名稱。"""
    for r in roles:
        shortname = r.get("shortname", "")
        if shortname in ("editingteacher", "teacher"):
            return t("members.teacher")
        if shortname == "student":
            return t("members.student")
    return roles[0].get("shortname", "—") if roles else "—"


@app.callback(invoke_without_command=True)
def members(
    course: str = typer.Option(..., "--course", "-c", help=t("members.opt_course")),
):
    """List course members."""
    client = get_client()
    info = get_site_info(client)
    all_courses = get_enrolled_courses(client, info["userid"])

    matches = fuzzy_match_course(all_courses, course)
    if not matches:
        console.print(f"[red]{t('dl.no_match', q=course)}[/red]")
        raise typer.Exit(1)

    target = matches[0]
    cid = target["id"]
    cname = target.get("shortname", "")

    users = get_enrolled_users(client, cid)

    # 分類：教師在前，學生在後
    teachers = [u for u in users if any(r.get("shortname") in ("editingteacher", "teacher") for r in u.get("roles", []))]
    students = [u for u in users if u not in teachers]

    table = Table(title=f"{t('members.title')} — {cname}", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("ID", style="dim", width=8)
    table.add_column(t("members.col_name"), style="bold")
    table.add_column(t("members.col_email"))
    table.add_column(t("members.col_role"), style="cyan")

    for i, u in enumerate(teachers + students, 1):
        table.add_row(
            str(i),
            str(u.get("id", "")),
            u.get("fullname", ""),
            u.get("email", "[dim]hidden[/dim]"),
            _role_name(u.get("roles", [])),
        )

    console.print(table)
    console.print(f"[dim]{t('members.total', n=len(users))}[/dim]")
