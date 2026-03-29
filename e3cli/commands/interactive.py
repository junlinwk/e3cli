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
from e3cli.api.forums import get_forum_discussions, get_forums
from e3cli.api.members import get_enrolled_users
from e3cli.api.messages import send_message
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client, get_db
from e3cli.config import load_config
from e3cli.credential import activate_profile, get_active_profile, list_profiles
from e3cli.formatting import format_duedate, format_submission_status, sort_assignments
from e3cli.i18n import t
from e3cli.semester import (
    filter_current_semester,
    format_semester,
    get_current_semester_code,
    group_by_semester,
)
from e3cli.tui_menu import MenuItem, show_menu_fullscreen, wait_for_back

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
    """按 Enter、← 或 q 返回。支援方向鍵。"""
    wait_for_back(t("tui.press_enter") + " ")


def _enter_shell():
    """進入互動式 shell 模式，路徑提示不可刪除。"""
    console.print(f"\n[yellow]{t('tui.shell_mode')}[/yellow]")
    shell = os.environ.get("SHELL", "/bin/bash")

    # 啟用 shell 模式的 tab 補全（用系統預設）
    if "libedit" in (readline.__doc__ or ""):
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    while True:
        try:
            cwd = os.getcwd()
            # 用 input() + ANSI prompt，路徑是 prompt 的一部分所以不可刪除
            prompt = f"\033[33m{cwd}\033[0m \033[1m$\033[0m "
            cmd = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if cmd in ("exit", "quit", ""):
            break

        # 處理 cd
        if cmd == "cd" or cmd.startswith("cd "):
            target = cmd[3:].strip() if cmd.startswith("cd ") else os.path.expanduser("~")
            target = os.path.expanduser(target)
            try:
                os.chdir(target)
            except OSError as e:
                console.print(f"[red]{e}[/red]")
            continue

        try:
            subprocess.run(cmd, shell=True, executable=shell)
        except Exception as e:
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

    last_cursor = 0
    active = get_active_profile()

    while True:
        console.print()
        console.print(Panel(
            f"[bold]{user}[/bold]  |  {sem}  |  {len(current_courses)} courses  |  [dim]profile: {active}[/dim]",
            title=f"[bold cyan]e3cli v{__version__}[/bold cyan]",
            border_style="cyan",
        ))

        items = [
            MenuItem(f"{t('tui.select_course')} ({sem})", key="current"),
            MenuItem(f"{t('tui.select_course')} ({t('sem.all_semesters')})", key="all"),
            MenuItem(t("tui.assignments"), key="assignments"),
            MenuItem(t("tui.sync_courses"), key="sync"),
            MenuItem(f"{t('profile.select')} [{active}]", key="profile"),
            MenuItem(t("tui.quit"), key="quit"),
        ]

        result = show_menu_fullscreen(items, title=t("tui.main_menu"), subtitle="↑↓ ←→ Enter / q", selected=last_cursor)
        last_cursor = result.cursor

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
        elif result.key == "profile":
            switched = _profile_menu()
            if switched:
                # 重新載入
                active = get_active_profile()
                client = get_client()
                cfg = load_config()
                info = get_site_info(client)
                all_courses = get_enrolled_courses(client, info["userid"])
                current_courses = filter_current_semester(all_courses)
                if not current_courses:
                    current_courses = all_courses
                user = info.get("fullname", "")


# ─── Course List ─────────────────────────────────────────────────────────

def _course_list_menu(client, db, cfg, info, courses, show_all=False):
    last_cursor = 0
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

        result = show_menu_fullscreen(items, title=t("tui.select_course"), subtitle=t("tui.search_hint"), selected=last_cursor)
        last_cursor = result.cursor

        if result.action in ("back", "quit"):
            break
        elif result.action == "select":
            target_id = result.key
            course = next((c for c in flat_list if str(c["id"]) == target_id), None)
            if course:
                _course_detail_menu(client, db, cfg, info, course)


# ─── Course Detail ───────────────────────────────────────────────────────

def _course_detail_menu(client, db, cfg, info, course):
    cid = course["id"]
    cname = course.get("shortname", "")
    cfull = course.get("fullname", cname)
    last_cursor = 0

    while True:
        console.print()
        summary = course.get("summary", "")
        if summary:
            short_intro = _strip_html(summary)
            if len(short_intro) > 120:
                short_intro = short_intro[:120] + "..."
            console.print(Panel(
                f"[bold]{cfull}[/bold]  [dim]({cname})[/dim]\n[dim]{short_intro}[/dim]",
                border_style="green",
            ))
        else:
            console.print(Panel(f"[bold]{cfull}[/bold]  [dim]({cname})[/dim]", border_style="green"))

        items = [
            MenuItem(t("course.intro"), key="intro"),
            MenuItem(t("tui.materials"), key="materials"),
            MenuItem(t("tui.assignments"), key="assignments"),
            MenuItem(t("announce.title"), key="announcements"),
            MenuItem(t("members.title"), key="members"),
            MenuItem(t("tui.grades"), key="grades"),
            MenuItem(t("tui.download_all"), key="download"),
            MenuItem(t("tui.back"), key="back"),
        ]

        result = show_menu_fullscreen(items, title=cfull, search_enabled=False, selected=last_cursor)
        last_cursor = result.cursor

        if result.action in ("back", "quit") or result.key == "back":
            break
        elif result.key == "intro":
            _course_intro_view(course)
        elif result.key == "materials":
            _materials_view(client, db, cfg, cid, cname)
        elif result.key == "assignments":
            _assignments_view(client, db, info, cid, cname)
        elif result.key == "announcements":
            _announcements_view(client, cid, cname)
        elif result.key == "members":
            _members_view(client, info, cid, cname)
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
        count = 0
        for cid, mid, fname, furl, fsize, ftime, section_name in all_files:
            if not db.is_downloaded(cid, mid, fname, ftime):
                dest = download_dir / _sanitize(cname) / _sanitize(section_name) / fname
                download_file(client, furl, dest)
                db.record_download(cid, mid, fname, furl, fsize, ftime, str(dest), int(time.time()))
                console.print(f"  {t('tui.downloaded', f=fname)}")
                count += 1
        if count > 0:
            console.print(f"[dim]{t('dl.saved_to', path=str(download_dir / _sanitize(cname)))}[/dim]")
        _wait_enter()
    elif result.action == "select":
        idx = int(result.key)
        if 0 <= idx < len(all_files):
            cid, mid, fname, furl, fsize, ftime, section_name = all_files[idx]
            dest = download_dir / _sanitize(cname) / _sanitize(section_name) / fname
            download_file(client, furl, dest)
            db.record_download(cid, mid, fname, furl, fsize, ftime, str(dest), int(time.time()))
            console.print(f"  {t('tui.downloaded', f=fname)}")
            console.print(f"[dim]{t('dl.saved_to', path=str(dest))}[/dim]")
            _wait_enter()


# ─── Assignments View ────────────────────────────────────────────────────

def _strip_html(html: str) -> str:
    """簡易 HTML 轉純文字。"""
    import html as html_module
    # 移除 HTML tags
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "  • ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_module.unescape(text)
    # 清理多餘空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
        # 附件數量提示
        attachments = a.get("introattachments", [])
        attach_hint = f" [dim]📎{len(attachments)}[/dim]" if attachments else ""
        row = [str(i)]
        if show_course:
            row.append(cname)
        row.extend([a["name"] + attach_hint, due, status_str])
        table.add_row(*row)

    console.print(table)


def _assignment_detail_view(client, db, cfg, assignment):
    """作業詳情頁：描述、附件、提交、編輯。"""
    aid = assignment["id"]
    aname = assignment["name"]
    intro = assignment.get("intro", "")
    attachments = assignment.get("introattachments", [])
    duedate = assignment.get("duedate", 0)

    while True:
        console.print()

        # 查詢繳交狀態和已提交的檔案
        sub_status = "new"
        submitted_files = []
        try:
            status_data = get_submission_status(client, aid)
            last_attempt = status_data.get("lastattempt", {})
            submission = last_attempt.get("submission", {})
            sub_status = submission.get("status", "new")
            # 取得已提交的檔案列表
            for plugin in submission.get("plugins", []):
                if plugin.get("type") == "file":
                    for area in plugin.get("fileareas", []):
                        submitted_files.extend(area.get("files", []))
        except Exception:
            pass

        # 標題 + 狀態
        status_str = format_submission_status(sub_status)
        console.print(Panel(
            f"[bold]{aname}[/bold]  (ID: {aid})\n{t('assign.col_status')}: {status_str}",
            border_style="yellow",
        ))

        # 截止日期
        console.print(f"  {t('assign.col_due')}: {format_duedate(duedate)}")
        console.print()

        # 描述
        console.print(f"[bold]{t('tui.assign_desc')}[/bold]")
        console.print("─" * min(console.width, 60))
        if intro:
            desc_text = _strip_html(intro)
            console.print(Panel(desc_text, border_style="dim", padding=(0, 1)))
        else:
            console.print(f"  [dim]{t('tui.assign_no_desc')}[/dim]")
        console.print()

        # 作業附件
        console.print(f"[bold]{t('tui.assign_attachments')}[/bold]")
        console.print("─" * min(console.width, 60))
        if attachments:
            for i, att in enumerate(attachments, 1):
                fname = att.get("filename", "?")
                fsize = att.get("filesize", 0)
                console.print(f"  [cyan]{i}[/cyan]  {fname}  [dim]({_format_size(fsize)})[/dim]")
        else:
            console.print(f"  [dim]{t('tui.assign_no_attach')}[/dim]")
        console.print()

        # 已繳交的檔案
        if submitted_files:
            console.print(f"[bold]{t('edit.current_files')}[/bold]")
            console.print("─" * min(console.width, 60))
            for sf in submitted_files:
                fname = sf.get("filename", "?")
                fsize = sf.get("filesize", 0)
                console.print(f"  [green]✓[/green] {fname}  [dim]({_format_size(fsize)})[/dim]")
            console.print()

        # 操作選單
        console.print(f"  [cyan]s[/cyan]  {t('tui.assign_submit')}")
        if sub_status in ("submitted", "draft"):
            console.print(f"  [cyan]e[/cyan]  {t('edit.reupload')}")
        if attachments:
            console.print(f"  [cyan]d[/cyan]  {t('tui.assign_dl_all_attach')}")
            console.print(f"  [cyan]1-{len(attachments)}[/cyan]  {t('tui.assign_dl_attach')}")
        console.print(f"  [cyan]q[/cyan]  {t('tui.back')}")
        console.print()

        choice = _prompt(t("tui.assign_detail"))

        if choice in ("q", "b", "back", ""):
            break
        elif choice == "s":
            _submit_interactive(client, db, assignment)
        elif choice == "e" and sub_status in ("submitted", "draft"):
            _edit_submission(client, db, assignment)
        elif choice == "d" and attachments:
            _download_attachments(client, cfg, attachments)
        elif choice.isdigit() and attachments:
            idx = int(choice) - 1
            if 0 <= idx < len(attachments):
                _download_attachments(client, cfg, [attachments[idx]])


def _download_attachments(client, cfg, attachments: list[dict]):
    """下載作業附件。"""
    download_dir = cfg.storage.download_dir / "_attachments"
    for att in attachments:
        fname = att.get("filename", "unknown")
        furl = att.get("fileurl", "")
        if not furl:
            continue
        dest = download_dir / fname
        download_file(client, furl, dest)
        console.print(f"  {t('tui.downloaded', f=fname)}")
    console.print(f"[dim]{t('dl.saved_to', path=str(download_dir))}[/dim]")


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

    while True:
        _show_assignments_table(sorted_raw, f"{t('tui.assignments')} — {cname}")
        console.print(f"\n[dim]{t('tui.view_detail')}[/dim]")
        choice = _prompt()

        if choice in ("q", "b", "back", ""):
            break
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(sorted_raw):
                cfg = load_config()
                _assignment_detail_view(client, db, cfg, sorted_raw[idx][0])


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

    while True:
        _show_assignments_table(sorted_raw, t("tui.assignments"), show_course=True)
        console.print(f"\n[dim]{t('tui.view_detail')}[/dim]")
        choice = _prompt()

        if choice in ("q", "b", "back", ""):
            break
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(sorted_raw):
                cfg = load_config()
                _assignment_detail_view(client, db, cfg, sorted_raw[idx][0])


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
    """設定 readline tab 補全為檔案路徑，行為同 bash/zsh。"""
    def _completer(text, state):
        expanded = os.path.expanduser(text) if text else ""
        # glob 匹配，加上隱藏檔支援
        pattern = expanded + "*"
        matches = glob.glob(pattern)
        # 也嘗試加 .* 匹配隱藏檔（如果使用者輸入了 .）
        if text.startswith("."):
            matches += glob.glob(expanded + "*")

        # 去重
        matches = sorted(set(matches))

        # 目錄加 /
        matches = [m + "/" if os.path.isdir(m) else m for m in matches]

        # 還原 ~ 前綴
        if text.startswith("~") and not expanded.startswith("~"):
            home = os.path.expanduser("~")
            matches = [m.replace(home, "~", 1) for m in matches]

        return matches[state] if state < len(matches) else None

    # 保存舊設定
    old_completer = readline.get_completer()
    old_delims = readline.get_completer_delims()

    readline.set_completer(_completer)
    readline.set_completer_delims(" \t\n;|&")
    # macOS 用 libedit，語法不同
    if "libedit" in (readline.__doc__ or ""):
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    return old_completer, old_delims


def _restore_tab_completion(old_state):
    """還原 readline 設定。"""
    if old_state:
        old_completer, old_delims = old_state
        readline.set_completer(old_completer)
        readline.set_completer_delims(old_delims)
    else:
        readline.set_completer(None)


def _input_with_readline(prompt_text: str) -> str:
    """用 Python 內建 input()（走 readline，支援 tab 補全）。"""
    try:
        return input(prompt_text).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return "q"


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
    old_state = _setup_tab_completion()

    while True:
        # 用 input() 而非 console.input()，這樣 readline/tab 才有效
        cwd = os.getcwd()
        file_input = _input_with_readline(f"\033[36m{cwd}\033[0m \033[1mfile>\033[0m ")

        if file_input in ("q", "b", "back"):
            _restore_tab_completion(old_state)
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
            _restore_tab_completion(old_state)
            return

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

        _restore_tab_completion(old_state)
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
        console.print(f"[dim]{t('dl.saved_to', path=str(download_dir / _sanitize(cname)))}[/dim]")
    _wait_enter()


# ─── Course Intro View ───────────────────────────────────────────────────

def _course_intro_view(course):
    """顯示課程簡介。"""
    console.print()
    cfull = course.get("fullname", "")
    summary = course.get("summary", "")

    console.print(Panel(f"[bold]{cfull}[/bold]", title=t("course.intro"), border_style="green"))

    if summary:
        desc = _strip_html(summary)
        console.print(Panel(desc, border_style="dim", padding=(0, 1)))
    else:
        console.print(f"  [dim]{t('course.no_intro')}[/dim]")

    _wait_enter()


# ─── Announcements View ─────────────────────────────────────────────────

def _announcements_view(client, cid, cname):
    """查看課程公告列表，可進入查看詳情。"""
    # 找公告論壇
    forums = get_forums(client, [cid])
    forum_id = None
    for f in forums:
        if f.get("type") == "news":
            forum_id = f["id"]
            break

    if forum_id is None:
        console.print(f"[yellow]{t('announce.no_forum')}[/yellow]")
        _wait_enter()
        return

    data = get_forum_discussions(client, forum_id, perpage=20)
    discussions = data.get("discussions", [])

    if not discussions:
        console.print(f"[dim]{t('announce.empty')}[/dim]")
        _wait_enter()
        return

    while True:
        from datetime import datetime as _dt

        table = Table(title=f"{t('announce.title')} — {cname}", show_lines=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column(t("announce.col_title"), style="bold")
        table.add_column(t("announce.col_author"), style="dim")
        table.add_column(t("announce.col_date"))

        for i, disc in enumerate(discussions, 1):
            ts = disc.get("timemodified", 0)
            dt = _dt.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "—"
            table.add_row(str(i), disc.get("name", ""), disc.get("userfullname", ""), dt)

        console.print(table)
        console.print(f"\n[dim]{t('announce.view_detail')}[/dim]")
        choice = _prompt()

        if choice in ("q", "b", "back", ""):
            break

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(discussions):
                _announcement_detail_view(discussions[idx])


def _announcement_detail_view(disc):
    """查看單一公告詳情。"""
    from datetime import datetime as _dt

    console.print()
    ts = disc.get("timemodified", 0)
    dt = _dt.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "—"

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
        console.print(f"\n[bold]📎 {t('tui.assign_attachments')}[/bold]")
        for att in attachments:
            fname = att.get("filename", "?")
            console.print(f"  {fname}")

    _wait_enter()


# ─── Members View ────────────────────────────────────────────────────────

def _members_view(client, info, cid, cname):
    """查看課程成員，可選擇發送訊息。"""
    users = get_enrolled_users(client, cid)

    # 分類
    teachers = []
    students = []
    for u in users:
        roles = u.get("roles", [])
        is_teacher = any(r.get("shortname") in ("editingteacher", "teacher") for r in roles)
        if is_teacher:
            teachers.append(u)
        else:
            students.append(u)

    all_users = teachers + students

    while True:
        table = Table(title=f"{t('members.title')} — {cname}", show_lines=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column(t("members.col_name"), style="bold")
        table.add_column(t("members.col_email"))
        table.add_column(t("members.col_role"), style="cyan")

        for i, u in enumerate(all_users, 1):
            roles = u.get("roles", [])
            is_teacher = any(r.get("shortname") in ("editingteacher", "teacher") for r in roles)
            role = t("members.teacher") if is_teacher else t("members.student")
            email = u.get("email", "")
            if not email:
                email = "[dim]—[/dim]"
            table.add_row(str(i), u.get("fullname", ""), email, role)

        console.print(table)
        console.print(f"[dim]{t('members.total', n=len(all_users))}[/dim]")
        console.print(f"\n[dim]{t('members.select_msg')}[/dim]")

        choice = _prompt()

        if choice in ("q", "b", "back", ""):
            break

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(all_users):
                _send_message_interactive(client, all_users[idx])


# ─── Message Interactive ─────────────────────────────────────────────────

def _send_message_interactive(client, user):
    """互動式發送訊息給指定使用者。"""
    uid = user.get("id")
    name = user.get("fullname", "")

    console.print(f"\n[bold]{t('msg.to', name=name)}[/bold] (ID: {uid})")
    console.print(f"[dim]{t('msg.content_prompt')}[/dim]")

    lines = []
    while True:
        try:
            line = input("  ")
            if line == "":
                break
            lines.append(line)
        except (EOFError, KeyboardInterrupt):
            print()
            break

    text = "\n".join(lines)
    if not text.strip():
        console.print(f"[dim]{t('msg.cancelled')}[/dim]")
        return

    # 預覽
    console.print("\n[dim]───[/dim]")
    console.print(text)
    console.print("[dim]───[/dim]")

    import typer as _typer
    confirm = _typer.confirm(t("msg.confirm"), default=True)
    if not confirm:
        console.print(f"[dim]{t('msg.cancelled')}[/dim]")
        return

    try:
        result = send_message(client, uid, text)
        if result and isinstance(result, list):
            err = result[0].get("errormessage", "")
            if err:
                console.print(f"[red]{t('msg.failed', e=err)}[/red]")
            else:
                console.print(f"[green]{t('msg.sent')}[/green]")
        else:
            console.print(f"[green]{t('msg.sent')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('msg.failed', e=str(e))}[/red]")

    _wait_enter()


# ─── Edit Submission ─────────────────────────────────────────────────────

def _edit_submission(client, db, assignment):
    """重新上傳覆蓋已繳交的作業。"""
    aid = assignment["id"]
    aname = assignment["name"]

    console.print(f"\n[bold]{t('edit.title')} — {aname}[/bold]")
    console.print(f"[yellow]{t('edit.reupload')}[/yellow]")

    # 顯示目前繳交的檔案
    try:
        status_data = get_submission_status(client, aid)
        submission = status_data.get("lastattempt", {}).get("submission", {})
        for plugin in submission.get("plugins", []):
            if plugin.get("type") == "file":
                for area in plugin.get("fileareas", []):
                    for sf in area.get("files", []):
                        console.print(f"  [dim]current:[/dim] {sf.get('filename', '?')}")
    except Exception:
        pass

    console.print()

    # 用跟 submit 一樣的檔案選擇流程
    _list_files_in_cwd()
    console.print(f"\n[dim]{t('tui.shell_hint')}[/dim]")

    old_state = _setup_tab_completion()

    while True:
        cwd = os.getcwd()
        file_input = _input_with_readline(f"\033[36m{cwd}\033[0m \033[1mfile>\033[0m ")

        if file_input in ("q", "b", "back"):
            _restore_tab_completion(old_state)
            return

        if not file_input:
            continue

        if file_input == "!":
            _enter_shell()
            _list_files_in_cwd()
            continue

        if file_input.startswith("!"):
            cmd = file_input[1:]
            shell = os.environ.get("SHELL", "/bin/bash")
            try:
                subprocess.run(cmd, shell=True, executable=shell)
            except Exception as e:
                console.print(f"[red]{e}[/red]")
            continue

        file_path = Path(file_input).expanduser().resolve()
        if not file_path.exists():
            console.print(f"[red]{t('submit.not_found', f=file_input)}[/red]")
            continue

        # 確認覆蓋
        import typer as _typer
        confirm = _typer.confirm(
            t("tui.confirm_submit", f=file_path.name, a=f"{aname} ({t('edit.reupload')})"),
            default=True,
        )
        if not confirm:
            console.print(f"[dim]{t('tui.submit_cancelled')}[/dim]")
            _restore_tab_completion(old_state)
            return

        # 上傳
        console.print(f"[dim]{t('submit.uploading', n=1)}[/dim]")
        result = client.upload_file(file_path)
        itemid = result[0].get("itemid", 0) if result else 0
        console.print(f"  ✓ {file_path.name}")

        # 重新提交
        console.print(f"[dim]{t('submit.submitting')}[/dim]")
        save_submission(client, aid, itemid)

        # 驗證
        verify = get_submission_status(client, aid)
        sub_status = verify.get("lastattempt", {}).get("submission", {}).get("status", "unknown")

        if sub_status in ("submitted", "draft"):
            console.print(f"[green]{t('edit.success')}[/green]")
            db.update_assignment_status(aid, sub_status)
        else:
            console.print(f"[yellow]Status: {sub_status}[/yellow]")

        _restore_tab_completion(old_state)
        _wait_enter()
        return


# ─── Profile Menu ─────────────────────────────────────────────────────────

def _profile_menu() -> bool:
    """帳號切換選單。回傳是否有切換。"""
    switched = False
    while True:
        profiles = list_profiles()

        items = []
        # 新增帳號選項在最上面
        items.append(MenuItem(f"+ {t('profile.add_new')}", key="_add_new"))

        if profiles:
            items.append(MenuItem("──────────", disabled=True))
            for p in profiles:
                marker = "● " if p["active"] else "  "
                items.append(MenuItem(
                    f"{marker}{p['name']}",
                    key=p["name"],
                    description=p["username"],
                ))

        result = show_menu_fullscreen(items, title=t("profile.select"), search_enabled=False)

        if result.action in ("back", "quit"):
            return switched

        if result.action == "select":
            if result.key == "_add_new":
                if _add_profile_interactive():
                    switched = True
                    return switched
                continue
            # 選擇了現有帳號 → 進入管理子選單
            sub_result = _profile_action_menu(result.key)
            if sub_result == "switched":
                switched = True
                return switched
            # "edited", "deleted", None → 留在 profile 列表
            continue

    return switched


def _profile_action_menu(name: str) -> str | None:
    """帳號管理子選單。回傳 "switched"/"edited"/"deleted"/None。"""
    active = get_active_profile()
    is_active = name == active

    items = []
    if not is_active:
        items.append(MenuItem(t("profile.switch"), key="switch"))
    items.append(MenuItem(t("profile.edit"), key="edit"))
    if not is_active:
        items.append(MenuItem(f"[red]{t('profile.delete')}[/red]", key="delete"))

    result = show_menu_fullscreen(items, title=t("profile.manage", name=name), search_enabled=False)

    if result.action in ("back", "quit"):
        return None

    if result.key == "switch":
        if activate_profile(name):
            console.print(f"[green]{t('profile.switched', name=name)}[/green]")
            return "switched"
        else:
            console.print(f"[red]{t('profile.not_found', name=name)}[/red]")
            _wait_enter()
            return None

    elif result.key == "edit":
        return _edit_profile_interactive(name)

    elif result.key == "delete":
        return _delete_profile_interactive(name)

    return None


def _edit_profile_interactive(name: str) -> str | None:
    """互動式編輯帳號（重新輸入帳密）。"""
    import getpass
    from e3cli.auth import AuthError, get_token
    from e3cli.config import load_config, save_token
    from e3cli.credential import (
        load_credentials,
        save_credentials,
        save_token_for_profile,
    )

    console.print(f"\n[bold]{t('profile.edit')} — {name}[/bold]")

    old_creds = load_credentials(name)
    old_user = old_creds[0] if old_creds else ""

    username = _prompt(f"{t('login.prompt_user')} [{old_user}]")
    if username in ("q", "b", "back"):
        return None
    if not username:
        username = old_user

    password = getpass.getpass(f"  {t('login.prompt_pass')}")
    if not password:
        console.print("[yellow]Cancelled[/yellow]")
        _wait_enter()
        return None

    cfg = load_config()
    console.print(f"[dim]{t('login.connecting', url=cfg.moodle.url)}[/dim]")
    try:
        token = get_token(cfg.moodle.url, username, password, cfg.moodle.service)
        save_token_for_profile(token, name)
        save_credentials(username, password, name)
        # 如果是 active profile，也更新主 token
        if name == get_active_profile():
            save_token(token)
        console.print(f"[green]{t('profile.edit_success', name=name)}[/green]")
        _wait_enter()
        return "edited"
    except AuthError as e:
        console.print(f"[red]✗ {e}[/red]")
        _wait_enter()
        return None


def _delete_profile_interactive(name: str) -> str | None:
    """互動式刪除帳號。"""
    from e3cli.credential import clear_credentials

    if name == get_active_profile():
        console.print(f"[red]{t('profile.cannot_delete_active')}[/red]")
        _wait_enter()
        return None

    console.print(f"\n[bold red]{t('profile.confirm_delete', name=name)}[/bold red]")
    ans = _prompt("y/N")
    if ans.lower() != "y":
        return None

    clear_credentials(name)
    console.print(f"[green]{t('profile.deleted', name=name)}[/green]")
    _wait_enter()
    return "deleted"


def _add_profile_interactive() -> bool:
    """互動式新增帳號。"""
    import getpass
    from e3cli.auth import AuthError, get_token
    from e3cli.config import load_config, save_token
    from e3cli.credential import save_credentials, save_token_for_profile

    console.print(f"\n[bold]{t('profile.add_new')}[/bold]")

    profile_name = _prompt("Profile name")
    if not profile_name or profile_name in ("q", "b", "back"):
        return False

    cfg = load_config()
    username = _prompt(t("login.prompt_user"))
    if not username or username in ("q", "b"):
        return False

    password = getpass.getpass(f"  {t('login.prompt_pass')}")

    console.print(f"[dim]{t('login.connecting', url=cfg.moodle.url)}[/dim]")
    try:
        token = get_token(cfg.moodle.url, username, password, cfg.moodle.service)
        save_token(token)
        save_token_for_profile(token, profile_name)
        save_credentials(username, password, profile_name)
        console.print(f"[green]{t('login.success_saved')} [profile: {profile_name}][/green]")
        _wait_enter()
        return True
    except AuthError as e:
        console.print(f"[red]✗ {e}[/red]")
        _wait_enter()
        return False


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
