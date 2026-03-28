"""e3cli interactive — 全互動式 TUI 介面，支援方向鍵導航。"""

from __future__ import annotations

import glob
import os
import re
import readline
import subprocess
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from e3cli import __version__
from e3cli.api.assignments import get_assignments, get_submission_status, get_submission_status_text, save_submission
from e3cli.api.courses import get_course_contents, get_enrolled_courses, get_grades
from e3cli.api.files import download_file
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client, get_db
from e3cli.config import load_config
from e3cli.formatting import format_duedate, format_submission_status, sort_assignments
from e3cli.i18n import t
from e3cli.semester import (
    filter_current_semester,
    format_semester,
    get_current_semester_code,
    group_by_semester,
)
from e3cli.tui_menu import MenuItem, show_menu_fullscreen

console = Console()
app = typer.Typer()


def _sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip().rstrip(".")


def _prompt(text: str = "") -> str:
    try:
        result = console.input(f"[cyan bold]{'> ' if not text else text + ' > '}[/cyan bold]").strip()
        return result if result else ""
    except (EOFError, KeyboardInterrupt):
        return "q"


def _wait_enter():
    """按 Enter 繼續。"""
    _prompt(t("tui.press_enter"))


def _enter_shell():
    """進入互動式 shell 模式。"""
    console.print(f"\n[yellow]{t('tui.shell_mode')}[/yellow]")
    shell = os.environ.get("SHELL", "/bin/bash")
    while True:
        try:
            cwd = os.getcwd()
            cmd = console.input(f"[yellow bold]{cwd} $ [/yellow bold]").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd in ("exit", "quit"):
            break
        if cmd == "\x1b" or not cmd:  # Esc or empty
            break

        try:
            subprocess.run(cmd, shell=True, executable=shell, cwd=cwd)
        except Exception as e:
            console.print(f"[red]{e}[/red]")

        # 支援 cd
        if cmd.startswith("cd "):
            target = cmd[3:].strip()
            target = os.path.expanduser(target)
            try:
                os.chdir(target)
            except OSError as e:
                console.print(f"[red]{e}[/red]")

    console.print(f"[dim]{t('tui.back')}[/dim]")


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.1f} MB"



# ─── Main Menu ───────────────────────────────────────────────────────────

def _main_menu(client, db, cfg, info, all_courses):
    current_courses = filter_current_semester(all_courses)
    if not current_courses:
        current_courses = all_courses

    sem = format_semester(get_current_semester_code())
    user = info.get("fullname", "")

    while True:
        console.print()
        console.print(Panel(
            f"[bold]{user}[/bold]  |  {sem}  |  {len(current_courses)} courses",
            title=f"[bold cyan]e3cli v{__version__}[/bold cyan]",
            border_style="cyan",
        ))

        items = [
            MenuItem(f"{t('tui.select_course')} ({sem})", key="current"),
            MenuItem(f"{t('tui.select_course')} ({t('sem.all_semesters')})", key="all"),
            MenuItem(t("tui.assignments"), key="assignments"),
            MenuItem(t("tui.sync_courses"), key="sync"),
            MenuItem(t("tui.quit"), key="quit"),
        ]

        result = show_menu_fullscreen(items, title=t("tui.main_menu"), subtitle="↑↓ ←→ Enter / q")

        if result.action == "quit" or result.key == "quit":
            break
        elif result.action == "back":
            break
        elif result.key == "current":
            _course_list_menu(client, db, cfg, info, current_courses)
        elif result.key == "all":
            _course_list_menu(client, db, cfg, info, all_courses, show_all=True)
        elif result.key == "assignments":
            _all_assignments_view(client, db, info, current_courses)
        elif result.key == "sync":
            _sync_menu(client, db, cfg, info, all_courses)


# ─── Course List ─────────────────────────────────────────────────────────

def _course_list_menu(client, db, cfg, info, courses, show_all=False):
    while True:
        items = []
        flat_list = []

        if show_all:
            groups = group_by_semester(courses)
            current = get_current_semester_code()
            for sem_code, sem_courses in groups.items():
                sem_label = format_semester(sem_code) if sem_code != "other" else t("sem.other")
                marker = " ★" if sem_code == current else ""
                items.append(MenuItem(f"── {sem_label}{marker} ──", disabled=True))
                for c in sem_courses:
                    items.append(MenuItem(
                        c.get("shortname", ""),
                        key=str(c["id"]),
                        description=c.get("fullname", ""),
                    ))
                    flat_list.append(c)
        else:
            for c in courses:
                items.append(MenuItem(
                    c.get("shortname", ""),
                    key=str(c["id"]),
                    description=c.get("fullname", ""),
                ))
                flat_list.append(c)

        result = show_menu_fullscreen(items, title=t("tui.select_course"), subtitle=t("tui.search_hint"))

        if result.action in ("back", "quit"):
            break
        elif result.action == "select":
            # 找到對應的課程
            target_id = result.key
            course = next((c for c in flat_list if str(c["id"]) == target_id), None)
            if course:
                _course_detail_menu(client, db, cfg, info, course)


# ─── Course Detail ───────────────────────────────────────────────────────

def _course_detail_menu(client, db, cfg, info, course):
    cid = course["id"]
    cname = course.get("shortname", "")
    cfull = course.get("fullname", cname)

    while True:
        console.print()
        console.print(Panel(f"[bold]{cfull}[/bold]  [dim]({cname})[/dim]", border_style="green"))

        items = [
            MenuItem(t("tui.materials"), key="materials"),
            MenuItem(t("tui.assignments"), key="assignments"),
            MenuItem(t("tui.grades"), key="grades"),
            MenuItem(t("tui.download_all"), key="download"),
            MenuItem(t("tui.back"), key="back"),
        ]

        result = show_menu_fullscreen(items, title=cfull, search_enabled=False)

        if result.action in ("back", "quit") or result.key == "back":
            break
        elif result.key == "materials":
            _materials_view(client, db, cfg, cid, cname)
        elif result.key == "assignments":
            _assignments_view(client, db, info, cid, cname)
        elif result.key == "grades":
            _grades_view(client, info, cid)
        elif result.key == "download":
            _download_course_all(client, db, cfg, cid, cname)


# ─── Materials View ──────────────────────────────────────────────────────

def _materials_view(client, db, cfg, cid, cname):
    contents = get_course_contents(client, cid)
    download_dir = cfg.storage.download_dir
    all_files = []

    items = []
    for section in contents:
        section_name = section.get("name", "unnamed")
        has_files = False
        for module in section.get("modules", []):
            mid = module.get("id", 0)
            for file_info in module.get("contents", []):
                fname = file_info.get("filename", "")
                furl = file_info.get("fileurl", "")
                fsize = file_info.get("filesize", 0)
                ftime = file_info.get("timemodified", 0)
                if not fname or not furl:
                    continue
                if not has_files:
                    items.append(MenuItem(f"── {section_name} ──", disabled=True))
                    has_files = True
                downloaded = db.is_downloaded(cid, mid, fname, ftime)
                prefix = "✓ " if downloaded else "  "
                items.append(MenuItem(
                    f"{prefix}{fname}",
                    key=str(len(all_files)),
                    description=_format_size(fsize),
                ))
                all_files.append((cid, mid, fname, furl, fsize, ftime, section_name))

    if not all_files:
        console.print(f"  [dim]{t('dl.no_new')}[/dim]")
        _wait_enter()
        return

    # 加入「全部下載」選項
    items.insert(0, MenuItem(f"↓ {t('tui.download_all')}", key="all"))

    result = show_menu_fullscreen(items, title=t("tui.materials"))

    if result.action in ("back", "quit"):
        return
    elif result.key == "all":
        for cid, mid, fname, furl, fsize, ftime, section_name in all_files:
            if not db.is_downloaded(cid, mid, fname, ftime):
                dest = download_dir / _sanitize(cname) / _sanitize(section_name) / fname
                download_file(client, furl, dest)
                db.record_download(cid, mid, fname, furl, fsize, ftime, str(dest), int(time.time()))
                console.print(f"  {t('tui.downloaded', f=fname)}")
        _wait_enter()
    elif result.action == "select":
        idx = int(result.key)
        if 0 <= idx < len(all_files):
            cid, mid, fname, furl, fsize, ftime, section_name = all_files[idx]
            dest = download_dir / _sanitize(cname) / _sanitize(section_name) / fname
            download_file(client, furl, dest)
            db.record_download(cid, mid, fname, furl, fsize, ftime, str(dest), int(time.time()))
            console.print(f"  {t('tui.downloaded', f=fname)}")
            _wait_enter()


# ─── Assignments View ────────────────────────────────────────────────────

def _show_assignments_table(assign_list: list[tuple], title: str, show_course: bool = False):
    """用 rich Table 顯示作業列表。assign_list: [(a, status, cname?), ...]"""
    table = Table(title=title, show_lines=True)
    table.add_column("#", style="cyan", width=4)
    if show_course:
        table.add_column(t("assign.col_course"), style="cyan")
    table.add_column(t("assign.col_name"), style="bold")
    table.add_column(t("assign.col_due"))
    table.add_column(t("assign.col_status"))

    for i, entry in enumerate(assign_list, 1):
        a, status = entry[0], entry[1]
        cname = entry[2] if len(entry) > 2 else ""
        due = format_duedate(a.get("duedate", 0))
        status_str = format_submission_status(status)
        row = [str(i)]
        if show_course:
            row.append(cname)
        row.extend([a["name"], due, status_str])
        table.add_row(*row)

    console.print(table)


def _assignments_view(client, db, info, cid, cname):
    data = get_assignments(client, [cid])
    raw = []

    console.print(f"[dim]{t('assign.checking_status')}[/dim]")
    for course_data in data.get("courses", []):
        for a in course_data.get("assignments", []):
            status = get_submission_status_text(client, a["id"])
            raw.append((a, status))

    sorted_raw = sort_assignments(raw)

    if not sorted_raw:
        console.print(f"  [green]{t('assign.empty')}[/green]")
        _wait_enter()
        return

    _show_assignments_table(sorted_raw, f"{t('tui.assignments')} — {cname}")

    console.print(f"\n[dim]{t('tui.submit_select')} (# to submit, q to go back)[/dim]")
    choice = _prompt()

    if choice in ("q", "b", "back", ""):
        return
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(sorted_raw):
            _submit_interactive(client, db, sorted_raw[idx][0])


def _all_assignments_view(client, db, info, courses):
    courseids = [c["id"] for c in courses]
    course_names = {c["id"]: c.get("shortname", "") for c in courses}

    if not courseids:
        console.print(f"[yellow]{t('common.no_courses')}[/yellow]")
        return

    data = get_assignments(client, courseids)
    raw = []

    console.print(f"[dim]{t('assign.checking_status')}[/dim]")
    for course_data in data.get("courses", []):
        cid = course_data["id"]
        cname = course_names.get(cid, "")
        for a in course_data.get("assignments", []):
            status = get_submission_status_text(client, a["id"])
            raw.append((a, status, cname))

    sorted_raw = sort_assignments(raw)

    if not sorted_raw:
        console.print(f"  [green]{t('assign.empty')}[/green]")
        _wait_enter()
        return

    _show_assignments_table(sorted_raw, t("tui.assignments"), show_course=True)

    console.print(f"\n[dim]{t('tui.submit_select')} (# to submit, q to go back)[/dim]")
    choice = _prompt()

    if choice in ("q", "b", "back", ""):
        return
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(sorted_raw):
            _submit_interactive(client, db, sorted_raw[idx][0])


# ─── Submit Interactive ──────────────────────────────────────────────────

def _list_files_in_cwd(max_show: int = 10):
    """列出當前目錄的檔案。"""
    cwd = Path.cwd()
    console.print(f"\n[dim]{t('tui.cwd', path=str(cwd))}[/dim]")
    console.print(f"[dim]{t('tui.files_in_dir')}[/dim]")

    entries = sorted(cwd.iterdir())
    files = [e for e in entries if e.is_file()]
    dirs = [e for e in entries if e.is_dir() and not e.name.startswith(".")]

    # 先顯示目錄
    for d in dirs[:5]:
        console.print(f"  [cyan]{d.name}/[/cyan]")

    # 再顯示檔案
    shown = 0
    for f in files:
        if shown >= max_show:
            remaining = len(files) - max_show
            console.print(f"  [dim]{t('tui.more_files', n=remaining)}[/dim]")
            break
        console.print(f"  {f.name}")
        shown += 1

    if not files and not dirs:
        console.print("  [dim](empty)[/dim]")


def _setup_tab_completion():
    """設定 readline tab 補全為檔案路徑。"""
    def _completer(text, state):
        # 展開 ~ 和環境變數
        expanded = os.path.expanduser(text)
        if os.path.isdir(expanded) and not expanded.endswith("/"):
            expanded += "/"
        matches = glob.glob(expanded + "*")
        # 目錄加 /
        matches = [m + "/" if os.path.isdir(m) else m for m in matches]
        # 如果原始輸入有 ~，把展開的路徑還原
        if text.startswith("~") and not expanded.startswith("~"):
            home = os.path.expanduser("~")
            matches = [m.replace(home, "~", 1) for m in matches]
        return matches[state] if state < len(matches) else None

    readline.set_completer(_completer)
    readline.set_completer_delims(" \t\n")
    readline.parse_and_bind("tab: complete")


def _submit_interactive(client, db, assignment):
    """互動式提交作業 — 顯示檔案列表、支援 tab 補全、! 進入 shell。"""
    aid = assignment["id"]
    aname = assignment["name"]

    console.print(f"\n[bold]{aname}[/bold] (ID: {aid})")

    # 列出當前目錄檔案
    _list_files_in_cwd()

    console.print(f"\n[dim]{t('tui.shell_hint')}[/dim]")
    console.print(f"[dim]{t('tui.submit_file_prompt')} (Tab {t('tui.back')}=q)[/dim]")

    # 啟用 tab 補全
    _setup_tab_completion()

    while True:
        file_input = _prompt(t("tui.submit_file_prompt"))

        if file_input in ("q", "b", "back"):
            # 還原 readline
            readline.set_completer(None)
            return

        if not file_input:
            # Enter 空白不做事（不返回）
            continue

        if file_input == "!":
            # 進入 shell 模式
            _enter_shell()
            _list_files_in_cwd()
            continue

        if file_input.startswith("!"):
            # 單次 shell 指令
            cmd = file_input[1:]
            shell = os.environ.get("SHELL", "/bin/bash")
            try:
                subprocess.run(cmd, shell=True, executable=shell)
            except Exception as e:
                console.print(f"[red]{e}[/red]")
            continue

        # 解析檔案路徑
        file_path = Path(file_input).expanduser().resolve()
        if not file_path.exists():
            console.print(f"[red]{t('submit.not_found', f=file_input)}[/red]")
            continue

        # 確認提交
        console.print()
        confirm = typer.confirm(t("tui.confirm_submit", f=file_path.name, a=aname), default=True)
        if not confirm:
            console.print(f"[dim]{t('tui.submit_cancelled')}[/dim]")
            continue

        # 上傳
        console.print(f"[dim]{t('submit.uploading', n=1)}[/dim]")
        result = client.upload_file(file_path)
        itemid = result[0].get("itemid", 0) if result else 0
        console.print(f"  ✓ {file_path.name}")

        # 提交
        console.print(f"[dim]{t('submit.submitting')}[/dim]")
        save_submission(client, aid, itemid)

        # 驗證
        verify = get_submission_status(client, aid)
        sub_status = verify.get("lastattempt", {}).get("submission", {}).get("status", "unknown")

        if sub_status == "submitted":
            console.print(f"[green]{t('submit.ok')}[/green]")
            db.update_assignment_status(aid, "submitted")
        elif sub_status == "draft":
            console.print(f"[yellow]{t('submit.draft')}[/yellow]")
        else:
            console.print(f"[yellow]Status: {sub_status}[/yellow]")

        # 還原 readline
        readline.set_completer(None)
        _wait_enter()
        return


# ─── Grades View ─────────────────────────────────────────────────────────

def _grades_view(client, info, cid):
    try:
        data = get_grades(client, cid, info["userid"])
    except Exception:
        console.print(f"[yellow]{t('tui.no_grades')}[/yellow]")
        _wait_enter()
        return

    grade_items = data.get("usergrades", [{}])[0].get("gradeitems", []) if data.get("usergrades") else []

    if not grade_items:
        console.print(f"[yellow]{t('tui.no_grades')}[/yellow]")
        _wait_enter()
        return

    table = Table(title=t("tui.grades"))
    table.add_column(t("tui.grade_item"), style="bold")
    table.add_column(t("tui.grade_value"), justify="right")
    table.add_column(t("tui.grade_range"), style="dim")
    table.add_column(t("tui.grade_pct"), justify="right")

    for item in grade_items:
        name = item.get("itemname", item.get("itemtype", "—"))
        grade = item.get("gradeformatted", "—")
        grade_min = item.get("grademin", 0)
        grade_max = item.get("grademax", 100)
        pct = item.get("percentageformatted", "—")
        table.add_row(name, str(grade), f"{grade_min}-{grade_max}", str(pct))

    console.print(table)
    _wait_enter()


# ─── Download All for Course ─────────────────────────────────────────────

def _download_course_all(client, db, cfg, cid, cname):
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
    _wait_enter()


# ─── Sync Menu ───────────────────────────────────────────────────────────

def _sync_menu(client, db, cfg, info, all_courses):
    current_courses = filter_current_semester(all_courses)
    if not current_courses:
        current_courses = all_courses

    items = [
        MenuItem(t("sem.current", sem=format_semester(get_current_semester_code())), key="current"),
        MenuItem(t("sem.all_semesters"), key="all"),
    ]

    result = show_menu_fullscreen(items, title=t("tui.sync_courses"), search_enabled=False)

    if result.action in ("back", "quit"):
        return
    elif result.key == "current":
        _do_sync_courses(client, db, cfg, current_courses)
    elif result.key == "all":
        _do_sync_courses(client, db, cfg, all_courses)


def _do_sync_courses(client, db, cfg, courses):
    from e3cli.api.assignments import get_assignments as _get_assignments
    from e3cli.api.courses import get_course_contents as _get_contents

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
            contents = _get_contents(client, cid)
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
                    if not fname or not furl or db.is_downloaded(cid, mid, fname, ftime):
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
            data = _get_assignments(client, courseids)
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
    _wait_enter()


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

    try:
        _main_menu(client, db, cfg, info, all_courses)
    except KeyboardInterrupt:
        pass
    finally:
        db.close()
