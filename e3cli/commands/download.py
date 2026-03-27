"""e3cli download — 下載課程教材。"""

from __future__ import annotations

import re
import time

import typer
from rich.console import Console
from rich.progress import Progress

from e3cli.api.courses import get_course_contents, get_enrolled_courses
from e3cli.api.files import download_file
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client, get_db
from e3cli.config import load_config

console = Console()
app = typer.Typer()


def _sanitize(name: str) -> str:
    """將名稱轉為安全的檔案系統路徑。"""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip().rstrip(".")


@app.callback(invoke_without_command=True)
def download(
    course: str = typer.Option(None, "--course", "-c", help="只下載特定課程 (課程代碼或名稱的子字串)"),
    all_courses: bool = typer.Option(False, "--all", "-a", help="下載所有課程的教材"),
):
    """下載課程教材到本地。"""
    if not course and not all_courses:
        console.print("[yellow]請指定 --course 或 --all[/yellow]")
        raise typer.Exit(1)

    client = get_client()
    db = get_db()
    cfg = load_config()
    download_dir = cfg.storage.download_dir

    info = get_site_info(client)
    course_list = get_enrolled_courses(client, info["userid"])

    # 過濾課程
    if course:
        course_lower = course.lower()
        course_list = [
            c for c in course_list
            if course_lower in c.get("shortname", "").lower()
            or course_lower in c.get("fullname", "").lower()
        ]
        if not course_list:
            console.print(f"[red]找不到符合 '{course}' 的課程[/red]")
            raise typer.Exit(1)

    total_new = 0
    total_skipped = 0

    for c in course_list:
        cid = c["id"]
        cname = _sanitize(c.get("shortname", str(cid)))
        db.upsert_course(cid, c.get("shortname", ""), c.get("fullname", ""))

        console.print(f"\n[bold cyan]📚 {c.get('fullname', cname)}[/bold cyan]")

        contents = get_course_contents(client, cid)
        files_to_download = []

        for section in contents:
            section_name = _sanitize(section.get("name", "未命名"))
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
            console.print("  [dim]沒有新檔案[/dim]")
            continue

        with Progress(console=console) as progress:
            task = progress.add_task("  下載中...", total=len(files_to_download))
            for cid, mid, fname, furl, fsize, ftime, dest in files_to_download:
                download_file(client, furl, dest)
                db.record_download(
                    cid, mid, fname, furl, fsize, ftime,
                    str(dest), int(time.time()),
                )
                total_new += 1
                progress.advance(task)

    console.print(f"\n[green]✓ 完成！下載 {total_new} 個新檔案，略過 {total_skipped} 個已存在的檔案。[/green]")
    db.close()
