"""e3cli schedule"""

from __future__ import annotations

import typer
from rich.console import Console

from e3cli.config import load_config
from e3cli.i18n import t
from e3cli.scheduler import cron

console = Console()
app = typer.Typer()


@app.command()
def enable(
    interval: int = typer.Option(None, "--interval", "-i", help=t("sched.opt_interval")),
):
    """Enable automatic sync (install cron job)."""
    cfg = load_config()
    minutes = interval or cfg.schedule.interval_minutes
    cron.install(minutes)
    console.print(f"[green]{t('sched.enabled', m=minutes)}[/green]")


@app.command()
def disable():
    """Disable automatic sync (remove cron job)."""
    cron.uninstall()
    console.print(f"[green]{t('sched.disabled')}[/green]")


@app.command()
def status():
    """Show current schedule status."""
    if cron.is_installed():
        line = cron.get_schedule_line()
        console.print(f"[green]{t('sched.status_on')}[/green]")
        console.print(f"  [dim]{line}[/dim]")
    else:
        console.print(f"[yellow]{t('sched.status_off')}[/yellow]")
