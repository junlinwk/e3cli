"""e3cli download — 預設只下載當期課程教材。"""

from __future__ import annotations

import re
import time

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from e3cli.api.courses import get_course_contents, get_enrolled_courses
from e3cli.api.files import download_file
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client, get_db
from e3cli.config import load_config
from e3cli.i18n import t
from e3cli.semester import filter_current_semester, fuzzy_match_course, get_current_semester_code, format_semester

console = Console()
app = typer.Typer()


def _sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip().rstrip(".")


def _interactive_select(course_list: list[dict]) -> list[dict]:
    """互動式選擇要下載的課程。"""
    table = Table(title=t("dl.select_prompt"))
    table.add_column("#", style="cyan", width=4)
    table.add_column(t("courses.col_code"), style="dim")
    table.add_column(t("courses.col_name"), style="bold")

    for i, c in enumerate(course_list, 1):
        table.add_row(str(i), c.get("shortname", ""), c.get("fullname", ""))

    console.print(table)
    raw = typer.prompt(t("tui.enter_number"), default="all")

    if raw.strip().lower() in ("all", "a"):
        return course_list

    selected = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(course_list):
                selected.append(course_list[idx])
    return selected if selected else course_list


def _do_download(client, db, course_list: list[dict], download_dir):
    """執行下載邏輯。"""
    total_new = 0
    total_skipped = 0

    for c in course_list:
        cid = c["id"]
        cname = _sanitize(c.get("shortname", str(cid)))
        db.upsert_course(cid, c.get("shortname", ""), c.get("fullname", ""))

        console.print(f"\n[bold cyan]{c.get('fullname', cname)}[/bold cyan]")

        contents = get_course_contents(client, cid)
        files_to_download = []

        for section in contents:
            section_name = _sanitize(section.get("name", "unnamed"))
            for module in section.get("modules", []):
                mid = module.get("id", 0)
                for file_info in module.get("contents", []):
                    fname = file_info.get("filename", "")
                    furl = file_info.get("fileurl", "")
                    fsize = file_info.get("filesize", 0)
                    ftime = file_info.get("timemodified", 0)

                    if not fname or not furl:
                        continue
                    if db.is_downloaded(cid, mid, fname, ftime):
                        total_skipped += 1
                        continue

                    dest = download_dir / cname / section_name / fname
                    files_to_download.append((cid, mid, fname, furl, fsize, ftime, dest))

        if not files_to_download:
            console.print(f"  [dim]{t('dl.no_new')}[/dim]")
            continue

        with Progress(console=console) as progress:
            task = progress.add_task(f"  {t('dl.progress')}", total=len(files_to_download))
            for cid, mid, fname, furl, fsize, ftime, dest in files_to_download:
                download_file(client, furl, dest)
                db.record_download(cid, mid, fname, furl, fsize, ftime, str(dest), int(time.time()))
                total_new += 1
                progress.advance(task)

    console.print(f"\n[green]{t('dl.done', new=total_new, skip=total_skipped)}[/green]")
    if total_new > 0:
        console.print(f"[dim]{t('dl.saved_to', path=str(download_dir))}[/dim]")


@app.callback(invoke_without_command=True)
def download(
    course: str = typer.Option(None, "--course", "-c", help=t("dl.opt_course")),
    all_courses: bool = typer.Option(False, "--all", "-a", help=t("dl.opt_all")),
    select: bool = typer.Option(False, "--select", "-s", help="Interactive course selection"),
):
    """Download course materials (current semester by default)."""
    client = get_client()
    db = get_db()
    cfg = load_config()
    download_dir = cfg.storage.download_dir

    info = get_site_info(client)
    all_course_list = get_enrolled_courses(client, info["userid"])

    if course:
        # CLI 指定課程名稱（模糊匹配）
        course_list = fuzzy_match_course(all_course_list, course)
        if not course_list:
            console.print(f"[red]{t('dl.no_match', q=course)}[/red]")
            raise typer.Exit(1)
    elif select:
        # 互動式選擇
        course_list = _interactive_select(all_course_list)
    elif all_courses:
        # 全部課程
        course_list = all_course_list
    else:
        # 預設：只抓當期課程
        course_list = filter_current_semester(all_course_list)
        if not course_list:
            console.print(f"[yellow]{t('dl.current_only')}[/yellow]")
            course_list = all_course_list
        else:
            sem = format_semester(get_current_semester_code())
            console.print(f"[dim]{t('sem.current', sem=sem)}[/dim]")

    if not course_list:
        console.print(f"[yellow]{t('courses.empty')}[/yellow]")
        raise typer.Exit()

    _do_download(client, db, course_list, download_dir)
    db.close()
