"""e3cli announcements — 查看課程公告。"""

from __future__ import annotations

import re
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from e3cli.api.courses import get_enrolled_courses
from e3cli.api.forums import get_forum_discussions, get_forums
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client
from e3cli.i18n import t
from e3cli.semester import fuzzy_match_course

console = Console()
app = typer.Typer()


def _strip_html(html: str) -> str:
    import html as html_module
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "  • ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_module.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _find_announcement_forum(client, cid: int) -> int | None:
    """找到課程的公告論壇 ID。"""
    forums = get_forums(client, [cid])
    for f in forums:
        if f.get("type") == "news":
            return f["id"]
    return None


@app.callback(invoke_without_command=True)
def announcements(
    course: str = typer.Option(..., "--course", "-c", help=t("announce.opt_course")),
    detail: int = typer.Option(None, "--detail", "-d", help="View announcement detail by discussion ID"),
):
    """View course announcements."""
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

    forum_id = _find_announcement_forum(client, cid)
    if forum_id is None:
        console.print(f"[yellow]{t('announce.no_forum')}[/yellow]")
        raise typer.Exit()

    data = get_forum_discussions(client, forum_id, perpage=20)
    discussions = data.get("discussions", [])

    if not discussions:
        console.print(f"[dim]{t('announce.empty')}[/dim]")
        raise typer.Exit()

    # --detail: 顯示單一公告
    if detail is not None:
        disc = next((d for d in discussions if d.get("id") == detail or d.get("discussion") == detail), None)
        if disc:
            ts = disc.get("timemodified", 0)
            dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "—"
            console.print(Panel(
                f"[bold]{disc.get('name', '')}[/bold]",
                subtitle=f"{disc.get('userfullname', '')}  |  {dt}",
                border_style="yellow",
            ))
            msg = disc.get("message", "")
            if msg:
                console.print(Panel(_strip_html(msg), border_style="dim", padding=(0, 1)))

            attachments = disc.get("attachments", [])
            if attachments:
                console.print("\n[bold]📎 Attachments[/bold]")
                for att in attachments:
                    console.print(f"  {att.get('filename', '?')}  [dim]{att.get('fileurl', '')}[/dim]")
        else:
            console.print(f"[red]Discussion ID {detail} not found[/red]")
        return

    # 列表
    table = Table(title=f"{t('announce.title')} — {cname}", show_lines=True)
    table.add_column("#", style="cyan", width=4)
    table.add_column("ID", style="dim", width=8)
    table.add_column(t("announce.col_title"), style="bold")
    table.add_column(t("announce.col_author"), style="dim")
    table.add_column(t("announce.col_date"))

    for i, disc in enumerate(discussions, 1):
        ts = disc.get("timemodified", 0)
        dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "—"
        disc_id = disc.get("discussion", disc.get("id", ""))
        table.add_row(
            str(i),
            str(disc_id),
            disc.get("name", ""),
            disc.get("userfullname", ""),
            dt,
        )

    console.print(table)
    console.print(f"\n[dim]Use e3cli announcements -c \"{course}\" --detail <ID> to view content[/dim]")
