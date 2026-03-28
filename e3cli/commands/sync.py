"""e3cli sync — 預設只同步當期課程。"""

from __future__ import annotations

import re
import time

import typer
from rich.console import Console
from rich.table import Table

from e3cli.api.assignments import get_assignments
from e3cli.api.courses import get_course_contents, get_enrolled_courses
from e3cli.api.files import download_file
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client, get_db
from e3cli.config import load_config
from e3cli.i18n import t
from e3cli.semester import (
    filter_current_semester,
    format_semester,
    fuzzy_match_course,
    get_current_semester_code,
)

console = Console()
app = typer.Typer()


def _sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip().rstrip(".")


def _interactive_select(course_list: list[dict]) -> list[dict]:
    """互動式選擇要同步的課程。"""
    table = Table(title=t("sync.select_prompt"))
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


@app.callback(invoke_without_command=True)
def sync(
    quiet: bool = typer.Option(False, "--quiet", "-q", help=t("sync.opt_quiet")),
    all_courses: bool = typer.Option(False, "--all", "-a", help="Sync all semesters"),
    course: str = typer.Option(
        None, "--course", "-c", help="Sync specific course (fuzzy match)"
    ),
    select: bool = typer.Option(
        False, "--select", "-s", help="Interactive course selection"
    ),
):
    """Sync course materials and assignments (current semester by default)."""
    client = get_client()
    db = get_db()
    cfg = load_config()
    download_dir = cfg.storage.download_dir
    now = int(time.time())

    info = get_site_info(client)
    userid = info["userid"]

    all_course_list = get_enrolled_courses(client, userid)

    # 決定要同步的課程
    if course:
        course_list = fuzzy_match_course(all_course_list, course)
    elif select and not quiet:
        course_list = _interactive_select(all_course_list)
    elif all_courses:
        course_list = all_course_list
    else:
        course_list = filter_current_semester(all_course_list)
        if not course_list:
            course_list = all_course_list
        elif not quiet:
            sem = format_semester(get_current_semester_code())
            console.print(f"[dim]{t('sem.current', sem=sem)}[/dim]")

    if not quiet:
        console.print(f"[bold]{t('sync.syncing', name=info['fullname'])}[/bold]\n")

    courseids = []
    course_names = {}

    for c in course_list:
        cid = c["id"]
        courseids.append(cid)
        course_names[cid] = c.get("shortname", "")
        db.upsert_course(cid, c.get("shortname", ""), c.get("fullname", ""))

    # 下載教材
    new_files = 0
    for c in course_list:
        cid = c["id"]
        cname = _sanitize(c.get("shortname", str(cid)))

        try:
            contents = get_course_contents(client, cid)
        except Exception:
            continue

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
                        continue

                    dest = download_dir / cname / section_name / fname
                    try:
                        download_file(client, furl, dest)
                        db.record_download(
                            cid, mid, fname, furl, fsize, ftime, str(dest), now
                        )
                        new_files += 1
                        if not quiet:
                            console.print(
                                f"  [green]↓[/green] {cname}/{section_name}/{fname}"
                            )
                    except Exception as e:
                        if not quiet:
                            console.print(f"  [red]✗[/red] {fname}: {e}")

        time.sleep(0.3)

    # 更新作業狀態
    new_assignments = 0
    if courseids:
        try:
            data = get_assignments(client, courseids)
            for course_data in data.get("courses", []):
                cid = course_data["id"]
                cname = course_names.get(cid, "")
                for a in course_data.get("assignments", []):
                    is_new = db.upsert_assignment(
                        a["id"],
                        cid,
                        cname,
                        a["name"],
                        a.get("duedate", 0),
                        now,
                    )
                    if is_new:
                        new_assignments += 1
                        if not quiet:
                            console.print(
                                f"  [yellow]{t('sync.new_assign', course=cname, name=a['name'])}[/yellow]"
                            )
        except Exception as e:
            if not quiet:
                console.print(f"[red]{t('sync.assign_fail', e=e)}[/red]")

    if not quiet:
        console.print(
            f"\n[green]{t('sync.done', files=new_files, assigns=new_assignments)}[/green]"
        )
        if new_files > 0:
            console.print(f"[dim]{t('dl.saved_to', path=str(download_dir))}[/dim]")

    db.close()
