"""e3cli assignments"""

from __future__ import annotations

import re
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from e3cli.api.assignments import get_assignments, get_submission_status_text
from e3cli.api.courses import get_enrolled_courses
from e3cli.api.files import download_file
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client, get_db
from e3cli.config import load_config
from e3cli.course_name import migrate_course_dir
from e3cli.course_name import display_name
from e3cli.formatting import format_duedate, format_submission_status, sort_assignments
from e3cli.i18n import t
from e3cli.semester import filter_current_semester

console = Console()
app = typer.Typer()


def _strip_html(html: str) -> str:
    """簡易 HTML 轉純文字。"""
    import html as html_module
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "  • ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_module.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip().rstrip(".")


def _download_attachments(client, attachments: list[dict], dest_dir: Path):
    """下載作業附件到 dest_dir，回傳已下載的路徑。"""
    saved = []
    for att in attachments:
        fname = att.get("filename", "")
        furl = att.get("fileurl", "")
        if not fname or not furl:
            continue
        dest = dest_dir / _sanitize(fname)
        download_file(client, furl, dest)
        saved.append(dest)
    return saved


def _truncate(text: str, max_len: int = 80) -> str:
    """截斷文字，保留第一行。"""
    first_line = text.split("\n")[0].strip()
    if len(first_line) > max_len:
        return first_line[:max_len - 3] + "..."
    return first_line


@app.callback(invoke_without_command=True)
def assignments(
    due_soon: int = typer.Option(None, "--due-soon", help=t("assign.opt_due_soon")),
    all_semesters: bool = typer.Option(False, "--all", "-a", help="Show all semesters"),
    detail: int = typer.Option(None, "--detail", "-d", help="Show detail for assignment ID"),
    download: bool = typer.Option(
        False, "--download", help="With --detail: download the assignment's attachments"
    ),
    output: Path = typer.Option(
        None, "--output", "-o",
        help="With --download: target directory (default: <download_dir>/<course>/_assignments/<name>)",
    ),
):
    """List assignments and deadlines with submission status."""
    if (download or output is not None) and detail is None:
        console.print("[red]--download / --output require --detail <ID>[/red]")
        raise typer.Exit(1)

    client = get_client()
    db = get_db()

    info = get_site_info(client)
    course_list = get_enrolled_courses(client, info["userid"])

    if not all_semesters:
        filtered = filter_current_semester(course_list)
        if filtered:
            course_list = filtered

    courseids = [c["id"] for c in course_list]
    course_names = {
        c["id"]: display_name(c.get("fullname", ""), c.get("shortname", ""))
        for c in course_list
    }

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

    # --detail: 顯示單一作業完整描述
    if detail is not None:
        target = next((item for item in raw_items if item[0]["id"] == detail), None)
        if target:
            a = target[0]
            console.print(Panel(f"[bold]{a['name']}[/bold]  (ID: {a['id']})", border_style="yellow"))
            console.print(f"  Due: {format_duedate(a.get('duedate', 0))}")
            console.print(f"  Status: {format_submission_status(target[1])}")
            console.print()

            intro = a.get("intro", "")
            if intro:
                console.print("[bold]Description[/bold]")
                console.print(Panel(_strip_html(intro), border_style="dim"))
            else:
                console.print("[dim](No description)[/dim]")

            attachments = a.get("introattachments", [])
            if attachments:
                console.print(f"\n[bold]Attachments ({len(attachments)})[/bold]")
                for att in attachments:
                    fname = att.get("filename", "?")
                    fsize = att.get("filesize", 0)
                    furl = att.get("fileurl", "")
                    size_str = f" ({fsize // 1024}KB)" if fsize else ""
                    url_str = f"  [dim]{furl}[/dim]" if furl else ""
                    console.print(f"  📎 {fname}{size_str}{url_str}")

            if download:
                if not attachments:
                    console.print("\n[yellow]No attachments to download[/yellow]")
                else:
                    if output is not None:
                        dest_dir = output.expanduser()
                    else:
                        download_dir = load_config().storage.download_dir
                        course = next((c for c in course_list if c["id"] == target[2]), {})
                        cdir = migrate_course_dir(
                            download_dir, course.get("fullname", ""), course.get("shortname", str(target[2]))
                        )
                        dest_dir = download_dir / cdir / "_assignments" / _sanitize(a["name"])
                    console.print()
                    for dest in _download_attachments(client, attachments, dest_dir):
                        console.print(f"  {t('tui.downloaded', f=dest.name)}")
                    console.print(f"[dim]{t('dl.saved_to', path=str(dest_dir))}[/dim]")
        else:
            console.print(f"[red]Assignment ID {detail} not found[/red]")
        db.close()
        return

    # 排序
    sorted_items = sort_assignments(raw_items, now)

    table = Table(title=t("assign.title"), show_lines=True)
    table.add_column(t("courses.col_id"), style="dim")
    table.add_column(t("assign.col_course"), style="cyan")
    table.add_column(t("assign.col_name"), style="bold")
    table.add_column(t("assign.col_due"))
    table.add_column(t("assign.col_status"))
    table.add_column("📎", justify="center", width=3)

    for a, status, cid, cname, duedate in sorted_items:
        attachments = a.get("introattachments", [])
        attach_count = str(len(attachments)) if attachments else ""
        desc_hint = ""
        intro = a.get("intro", "")
        if intro:
            short = _truncate(_strip_html(intro), 40)
            if short:
                desc_hint = f"\n[dim]{short}[/dim]"

        table.add_row(
            str(a["id"]),
            cname,
            a["name"] + desc_hint,
            format_duedate(duedate),
            format_submission_status(status),
            attach_count,
        )

    console.print(table)
    console.print("\n[dim]Use e3cli assignments --detail <ID> to view full description[/dim]")
    db.close()
