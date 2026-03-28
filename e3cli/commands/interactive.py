"""e3cli interactive — 全互動式 TUI 介面。"""

from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from e3cli import __version__
from e3cli.api.assignments import get_assignments, get_submission_status, save_submission
from e3cli.api.courses import get_course_contents, get_enrolled_courses, get_grades
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
    group_by_semester,
)

console = Console()
app = typer.Typer()


def _sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip().rstrip(".")


def _clear():
    console.print("\n" * 2)


def _prompt(text: str = "") -> str:
    """顯示提示並取得使用者輸入。"""
    try:
        return console.input(f"[cyan bold]{'> ' if not text else text + ' > '}[/cyan bold]").strip()
    except (EOFError, KeyboardInterrupt):
        return "q"


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.1f} MB"


def _format_duedate(ts: int) -> str:
    if ts == 0:
        return t("assign.no_deadline")
    dt = datetime.fromtimestamp(ts)
    remaining = ts - int(time.time())
    days = remaining // 86400
    if remaining < 0:
        return f"[red]{dt:%m/%d %H:%M} ({t('assign.expired')})[/red]"
    if days <= 3:
        return f"[red]{dt:%m/%d %H:%M} ({t('assign.days_left', n=days)})[/red]"
    if days <= 7:
        return f"[yellow]{dt:%m/%d %H:%M} ({t('assign.days_left', n=days)})[/yellow]"
    return f"{dt:%m/%d %H:%M} ({t('assign.days_left', n=days)})"


# ─── Main Menu ───────────────────────────────────────────────────────────

def _main_menu(client, db, cfg, info, all_courses):
    """主選單迴圈。"""
    current_courses = filter_current_semester(all_courses)
    if not current_courses:
        current_courses = all_courses

    while True:
        sem = format_semester(get_current_semester_code())
        console.print()
        console.print(Panel(
            f"[bold]{info['fullname']}[/bold] | {sem} | {len(current_courses)} courses",
            title=f"[bold cyan]e3cli v{__version__}[/bold cyan]",
            border_style="cyan",
        ))

        console.print(f"  [cyan]1[/cyan]  {t('tui.select_course')} ({t('sem.current', sem=sem)})")
        console.print(f"  [cyan]2[/cyan]  {t('tui.select_course')} ({t('sem.all_semesters')})")
        console.print(f"  [cyan]3[/cyan]  {t('tui.assignments')}")
        console.print(f"  [cyan]4[/cyan]  {t('tui.sync_courses')}")
        console.print(f"  [cyan]5[/cyan]  {t('tui.search_hint').split(',')[0]}")
        console.print(f"  [cyan]q[/cyan]  {t('tui.quit')}")
        console.print()

        choice = _prompt(t("tui.main_menu"))

        if choice == "1":
            _course_list_menu(client, db, cfg, info, current_courses)
        elif choice == "2":
            _course_list_menu(client, db, cfg, info, all_courses, show_all=True)
        elif choice == "3":
            _all_assignments_view(client, db, info, current_courses)
        elif choice == "4":
            _sync_menu(client, db, cfg, info, all_courses)
        elif choice == "5":
            _search_menu(client, db, cfg, info, all_courses)
        elif choice in ("q", "quit", "exit"):
            console.print(f"[dim]{t('tui.quit')}[/dim]")
            break


# ─── Course List ─────────────────────────────────────────────────────────

def _course_list_menu(client, db, cfg, info, courses, show_all=False):
    """課程列表選擇。"""
    while True:
        _clear()

        if show_all:
            groups = group_by_semester(courses)
            current = get_current_semester_code()
            flat_list = []

            for sem_code, sem_courses in groups.items():
                sem_label = format_semester(sem_code) if sem_code != "other" else t("sem.other")
                marker = " ★" if sem_code == current else ""
                console.print(f"[bold]── {sem_label}{marker} ──[/bold]")

                for c in sem_courses:
                    idx = len(flat_list) + 1
                    console.print(f"  [cyan]{idx:3d}[/cyan]  {c.get('shortname', '')}  [dim]{c.get('fullname', '')}[/dim]")
                    flat_list.append(c)
                console.print()
        else:
            flat_list = courses
            for i, c in enumerate(courses, 1):
                console.print(f"  [cyan]{i:3d}[/cyan]  {c.get('shortname', '')}  [dim]{c.get('fullname', '')}[/dim]")

        console.print(f"\n  [dim]{t('tui.search_hint')}[/dim]")
        choice = _prompt(t("tui.select_course"))

        if choice in ("q", "b", "back"):
            break

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(flat_list):
                _course_detail_menu(client, db, cfg, info, flat_list[idx])
        else:
            # 模糊搜尋
            matches = fuzzy_match_course(flat_list, choice)
            if len(matches) == 1:
                _course_detail_menu(client, db, cfg, info, matches[0])
            elif matches:
                _course_list_menu(client, db, cfg, info, matches)
            else:
                console.print(f"[red]{t('dl.no_match', q=choice)}[/red]")


# ─── Course Detail ───────────────────────────────────────────────────────

def _course_detail_menu(client, db, cfg, info, course):
    """進入單一課程查看教材/作業/成績。"""
    cid = course["id"]
    cname = course.get("shortname", "")
    cfull = course.get("fullname", cname)

    while True:
        _clear()
        console.print(Panel(f"[bold]{cfull}[/bold]  [dim]({cname})[/dim]", border_style="green"))

        console.print(f"  [cyan]1[/cyan]  {t('tui.materials')}")
        console.print(f"  [cyan]2[/cyan]  {t('tui.assignments')}")
        console.print(f"  [cyan]3[/cyan]  {t('tui.grades')}")
        console.print(f"  [cyan]4[/cyan]  {t('tui.download_all')}")
        console.print(f"  [cyan]q[/cyan]  {t('tui.back')}")
        console.print()

        choice = _prompt(t("tui.course_menu"))

        if choice == "1":
            _materials_view(client, db, cfg, cid, cname)
        elif choice == "2":
            _assignments_view(client, db, info, cid, cname)
        elif choice == "3":
            _grades_view(client, info, cid)
        elif choice == "4":
            _download_course_all(client, db, cfg, cid, cname)
        elif choice in ("q", "b", "back"):
            break


# ─── Materials View ──────────────────────────────────────────────────────

def _materials_view(client, db, cfg, cid, cname):
    """查看課程教材，支援選擇下載。"""
    contents = get_course_contents(client, cid)
    download_dir = cfg.storage.download_dir

    all_files = []

    table = Table(title=t("tui.materials"))
    table.add_column("#", style="cyan", width=4)
    table.add_column(t("tui.file_section"), style="dim")
    table.add_column(t("tui.file_name"), style="bold")
    table.add_column(t("tui.file_size"), justify="right")

    for section in contents:
        section_name = section.get("name", "unnamed")
        for module in section.get("modules", []):
            mid = module.get("id", 0)
            for file_info in module.get("contents", []):
                fname = file_info.get("filename", "")
                furl = file_info.get("fileurl", "")
                fsize = file_info.get("filesize", 0)
                ftime = file_info.get("timemodified", 0)
                if not fname or not furl:
                    continue

                idx = len(all_files) + 1
                downloaded = db.is_downloaded(cid, mid, fname, ftime)
                status = "[green]✓[/green]" if downloaded else " "
                table.add_row(f"{status}{idx}", section_name, fname, _format_size(fsize))
                all_files.append((cid, mid, fname, furl, fsize, ftime, section_name))

    console.print(table)

    if not all_files:
        _prompt(t("tui.back"))
        return

    console.print(f"\n[dim]{t('tui.select_download')}[/dim]")
    choice = _prompt()

    if choice in ("q", "b", "back"):
        return

    if choice.lower() == "a":
        indices = range(len(all_files))
    else:
        indices = []
        for part in choice.split(","):
            part = part.strip()
            if "-" in part:
                bounds = part.split("-")
                if len(bounds) == 2 and bounds[0].isdigit() and bounds[1].isdigit():
                    indices.extend(range(int(bounds[0]) - 1, int(bounds[1])))
            elif part.isdigit():
                indices.append(int(part) - 1)

    for idx in indices:
        if 0 <= idx < len(all_files):
            cid, mid, fname, furl, fsize, ftime, section_name = all_files[idx]
            dest = download_dir / _sanitize(cname) / _sanitize(section_name) / fname
            download_file(client, furl, dest)
            db.record_download(cid, mid, fname, furl, fsize, ftime, str(dest), int(time.time()))
            console.print(f"  {t('tui.downloaded', f=fname)}")


# ─── Assignments View ────────────────────────────────────────────────────

def _assignments_view(client, db, info, cid, cname):
    """查看單一課程的作業，支援提交。"""
    data = get_assignments(client, [cid])

    assign_list = []
    table = Table(title=f"{t('tui.assignments')} — {cname}")
    table.add_column("#", style="cyan", width=4)
    table.add_column("ID", style="dim")
    table.add_column(t("assign.col_name"), style="bold")
    table.add_column(t("assign.col_due"))
    table.add_column(t("assign.col_status"))

    for course_data in data.get("courses", []):
        for a in course_data.get("assignments", []):
            idx = len(assign_list) + 1
            assign_list.append(a)
            table.add_row(
                str(idx),
                str(a["id"]),
                a["name"],
                _format_duedate(a.get("duedate", 0)),
                "—",
            )

    console.print(table)

    if not assign_list:
        _prompt(t("tui.back"))
        return

    console.print(f"\n[dim]{t('tui.submit_select')} (# to submit, q to go back)[/dim]")
    choice = _prompt()

    if choice in ("q", "b", "back"):
        return

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(assign_list):
            _submit_interactive(client, db, assign_list[idx])


def _all_assignments_view(client, db, info, courses):
    """查看所有課程的作業。"""
    courseids = [c["id"] for c in courses]
    course_names = {c["id"]: c.get("shortname", "") for c in courses}

    if not courseids:
        console.print(f"[yellow]{t('common.no_courses')}[/yellow]")
        _prompt(t("tui.back"))
        return

    data = get_assignments(client, courseids)

    assign_list = []
    table = Table(title=t("tui.assignments"))
    table.add_column("#", style="cyan", width=4)
    table.add_column(t("assign.col_course"), style="cyan")
    table.add_column(t("assign.col_name"), style="bold")
    table.add_column(t("assign.col_due"))

    for course_data in data.get("courses", []):
        cid = course_data["id"]
        cname = course_names.get(cid, "")
        for a in course_data.get("assignments", []):
            idx = len(assign_list) + 1
            assign_list.append(a)
            table.add_row(str(idx), cname, a["name"], _format_duedate(a.get("duedate", 0)))

    console.print(table)

    if not assign_list:
        console.print(f"[green]{t('assign.empty')}[/green]")
        _prompt(t("tui.back"))
        return

    console.print(f"\n[dim]{t('tui.submit_select')} (# to submit, q to go back)[/dim]")
    choice = _prompt()

    if choice in ("q", "b", "back"):
        return

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(assign_list):
            _submit_interactive(client, db, assign_list[idx])


# ─── Submit Interactive ──────────────────────────────────────────────────

def _submit_interactive(client, db, assignment):
    """互動式提交作業。"""
    aid = assignment["id"]
    aname = assignment["name"]

    console.print(f"\n[bold]{aname}[/bold] (ID: {aid})")

    file_path_str = _prompt(t("tui.submit_file_prompt"))
    if file_path_str in ("q", "b", "back", ""):
        return

    file_path = Path(file_path_str).expanduser()
    if not file_path.exists():
        console.print(f"[red]{t('submit.not_found', f=file_path)}[/red]")
        return

    console.print(f"[dim]{t('submit.uploading', n=1)}[/dim]")
    result = client.upload_file(file_path)
    itemid = result[0].get("itemid", 0) if result else 0
    console.print(f"  ✓ {file_path.name}")

    console.print(f"[dim]{t('submit.submitting')}[/dim]")
    save_submission(client, aid, itemid)

    verify = get_submission_status(client, aid)
    sub_status = verify.get("lastattempt", {}).get("submission", {}).get("status", "unknown")

    if sub_status == "submitted":
        console.print(f"[green]{t('submit.ok')}[/green]")
        db.update_assignment_status(aid, "submitted")
    elif sub_status == "draft":
        console.print(f"[yellow]{t('submit.draft')}[/yellow]")
    else:
        console.print(f"[yellow]Status: {sub_status}[/yellow]")

    _prompt(t("tui.back"))


# ─── Grades View ─────────────────────────────────────────────────────────

def _grades_view(client, info, cid):
    """查看課程成績。"""
    try:
        data = get_grades(client, cid, info["userid"])
    except Exception:
        console.print(f"[yellow]{t('tui.no_grades')}[/yellow]")
        _prompt(t("tui.back"))
        return

    items = data.get("usergrades", [{}])[0].get("gradeitems", []) if data.get("usergrades") else []

    if not items:
        console.print(f"[yellow]{t('tui.no_grades')}[/yellow]")
        _prompt(t("tui.back"))
        return

    table = Table(title=t("tui.grades"))
    table.add_column(t("tui.grade_item"), style="bold")
    table.add_column(t("tui.grade_value"), justify="right")
    table.add_column(t("tui.grade_range"), style="dim")
    table.add_column(t("tui.grade_pct"), justify="right")

    for item in items:
        name = item.get("itemname", item.get("itemtype", "—"))
        grade = item.get("gradeformatted", "—")
        grade_min = item.get("grademin", 0)
        grade_max = item.get("grademax", 100)
        pct = item.get("percentageformatted", "—")
        table.add_row(name, str(grade), f"{grade_min}-{grade_max}", str(pct))

    console.print(table)
    _prompt(t("tui.back"))


# ─── Download All for Course ─────────────────────────────────────────────

def _download_course_all(client, db, cfg, cid, cname):
    """下載某門課的所有教材。"""
    download_dir = cfg.storage.download_dir
    contents = get_course_contents(client, cid)
    count = 0

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

                dest = download_dir / _sanitize(cname) / section_name / fname
                download_file(client, furl, dest)
                db.record_download(cid, mid, fname, furl, fsize, ftime, str(dest), int(time.time()))
                console.print(f"  {t('tui.downloaded', f=fname)}")
                count += 1

    if count == 0:
        console.print(f"  [dim]{t('dl.no_new')}[/dim]")
    else:
        console.print(f"\n[green]{t('dl.done', new=count, skip=0)}[/green]")

    _prompt(t("tui.back"))


# ─── Sync Menu ───────────────────────────────────────────────────────────

def _sync_menu(client, db, cfg, info, all_courses):
    """同步選單。"""
    current_courses = filter_current_semester(all_courses)
    if not current_courses:
        current_courses = all_courses

    console.print(f"\n  [cyan]1[/cyan]  {t('sem.current', sem=format_semester(get_current_semester_code()))}")
    console.print(f"  [cyan]2[/cyan]  {t('sem.all_semesters')}")
    console.print(f"  [cyan]q[/cyan]  {t('tui.back')}")
    console.print()

    choice = _prompt(t("tui.sync_courses"))

    if choice == "1":
        # 直接呼叫 sync 邏輯而非 typer command
        _do_sync_courses(client, db, cfg, info, current_courses)
    elif choice == "2":
        _do_sync_courses(client, db, cfg, info, all_courses)


def _do_sync_courses(client, db, cfg, info, courses):
    """直接同步指定課程。"""
    from e3cli.api.assignments import get_assignments
    from e3cli.api.courses import get_course_contents

    download_dir = cfg.storage.download_dir
    now = int(time.time())
    new_files = 0
    new_assignments = 0

    courseids = []
    course_names = {}
    for c in courses:
        cid = c["id"]
        courseids.append(cid)
        course_names[cid] = c.get("shortname", "")

    for c in courses:
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
                        db.record_download(cid, mid, fname, furl, fsize, ftime, str(dest), now)
                        new_files += 1
                        console.print(f"  [green]↓[/green] {cname}/{section_name}/{fname}")
                    except Exception as e:
                        console.print(f"  [red]✗[/red] {fname}: {e}")

    if courseids:
        try:
            data = get_assignments(client, courseids)
            for course_data in data.get("courses", []):
                cid = course_data["id"]
                cname = course_names.get(cid, "")
                for a in course_data.get("assignments", []):
                    is_new = db.upsert_assignment(a["id"], cid, cname, a["name"], a.get("duedate", 0), now)
                    if is_new:
                        new_assignments += 1
                        console.print(f"  [yellow]{t('sync.new_assign', course=cname, name=a['name'])}[/yellow]")
        except Exception:
            pass

    console.print(f"\n[green]{t('sync.done', files=new_files, assigns=new_assignments)}[/green]")
    _prompt(t("tui.back"))


# ─── Search Menu ─────────────────────────────────────────────────────────

def _search_menu(client, db, cfg, info, all_courses):
    """模糊搜尋課程。"""
    query = _prompt(t("tui.select_course"))
    if query in ("q", "b", "back"):
        return

    matches = fuzzy_match_course(all_courses, query)
    if not matches:
        console.print(f"[red]{t('dl.no_match', q=query)}[/red]")
        return

    if len(matches) == 1:
        _course_detail_menu(client, db, cfg, info, matches[0])
    else:
        _course_list_menu(client, db, cfg, info, matches)


# ─── Entry Point ─────────────────────────────────────────────────────────

@app.callback(invoke_without_command=True)
def interactive():
    """Launch interactive TUI mode."""
    client = get_client()
    db = get_db()
    cfg = load_config()

    info = get_site_info(client)
    all_courses = get_enrolled_courses(client, info["userid"])

    if not all_courses:
        console.print(f"[yellow]{t('courses.empty')}[/yellow]")
        raise typer.Exit()

    _main_menu(client, db, cfg, info, all_courses)
    db.close()
