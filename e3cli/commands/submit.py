"""e3cli submit"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from e3cli.api.assignments import get_submission_status, save_submission
from e3cli.commands._common import get_client, get_db
from e3cli.i18n import t

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def submit(
    assignment_id: int = typer.Argument(..., help="Assignment ID"),
    files: list[Path] = typer.Argument(..., help="File(s) to submit"),
    text: str = typer.Option("", "--text", "-t", help=t("submit.opt_text")),
    force: bool = typer.Option(False, "--force", "-f", help=t("submit.opt_force")),
):
    """Upload and submit an assignment."""
    for f in files:
        if not f.exists():
            console.print(f"[red]✗ {t('submit.not_found', f=f)}[/red]")
            raise typer.Exit(1)

    client = get_client()
    db = get_db()

    console.print(f"[dim]{t('submit.checking', id=assignment_id)}[/dim]")
    try:
        status = get_submission_status(client, assignment_id)
    except Exception as e:
        console.print(f"[red]{t('submit.check_fail', e=e)}[/red]")
        raise typer.Exit(1)

    assign_info = status.get("lastattempt", {}).get("assign", {})
    duedate = assign_info.get("duedate", 0)
    if duedate and duedate < int(time.time()) and not force:
        dt = datetime.fromtimestamp(duedate).strftime("%Y-%m-%d %H:%M")
        console.print(f"[red]✗ {t('submit.past_due', dt=dt)}[/red]")
        raise typer.Exit(1)

    console.print(f"[dim]{t('submit.uploading', n=len(files))}[/dim]")
    itemid = 0
    for f in files:
        result = client.upload_file(f, itemid=itemid)
        if result and isinstance(result, list):
            itemid = result[0].get("itemid", itemid)
        console.print(f"  ✓ {f.name}")

    console.print(f"[dim]{t('submit.submitting')}[/dim]")
    save_submission(client, assignment_id, itemid, text)

    verify = get_submission_status(client, assignment_id)
    sub_status = (
        verify.get("lastattempt", {})
        .get("submission", {})
        .get("status", "unknown")
    )

    if sub_status == "submitted":
        console.print(f"[green]{t('submit.ok')}[/green]")
        db.update_assignment_status(assignment_id, "submitted")
    elif sub_status == "draft":
        console.print(f"[yellow]{t('submit.draft')}[/yellow]")
        db.update_assignment_status(assignment_id, "draft")
    else:
        console.print(f"[yellow]⚠ Status: {sub_status}[/yellow]")

    db.close()
