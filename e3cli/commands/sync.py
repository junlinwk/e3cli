"""e3cli sync"""

from __future__ import annotations

import re
import time

import typer
from rich.console import Console

from e3cli.api.assignments import get_assignments
from e3cli.api.courses import get_course_contents, get_enrolled_courses
from e3cli.api.files import download_file
from e3cli.api.site import get_site_info
from e3cli.commands._common import get_client, get_db
from e3cli.config import load_config
from e3cli.i18n import t

console = Console()
app = typer.Typer()


def _sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip().rstrip(".")


@app.callback(invoke_without_command=True)
def sync(
    quiet: bool = typer.Option(False, "--quiet", "-q", help=t("sync.opt_quiet")),
):
    """Sync all course materials and assignment status."""
    client = get_client()
    db = get_db()
    cfg = load_config()
    download_dir = cfg.storage.download_dir
    now = int(time.time())

    info = get_site_info(client)
    userid = info["userid"]
    if not quiet:
        console.print(f"[bold]{t('sync.syncing', name=info['fullname'])}[/bold]\n")

    course_list = get_enrolled_courses(client, userid)
    courseids = []
    course_names = {}

    for c in course_list:
        cid = c["id"]
        courseids.append(cid)
        course_names[cid] = c.get("shortname", "")
        db.upsert_course(cid, c.get("shortname", ""), c.get("fullname", ""))

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
                        db.record_download(cid, mid, fname, furl, fsize, ftime, str(dest), now)
                        new_files += 1
                        if not quiet:
                            console.print(f"  [green]↓[/green] {cname}/{section_name}/{fname}")
                    except Exception as e:
                        if not quiet:
                            console.print(f"  [red]✗[/red] {fname}: {e}")

        time.sleep(0.3)

    new_assignments = 0
    if courseids:
        try:
            data = get_assignments(client, courseids)
            for course in data.get("courses", []):
                cid = course["id"]
                cname = course_names.get(cid, "")
                for a in course.get("assignments", []):
                    is_new = db.upsert_assignment(
                        a["id"], cid, cname, a["name"], a.get("duedate", 0), now,
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
        console.print(f"\n[green]{t('sync.done', files=new_files, assigns=new_assignments)}[/green]")

    db.close()
