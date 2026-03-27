"""E3CLI 主入口 — 組裝所有子指令。"""

from __future__ import annotations

import sys

import typer

from e3cli import __version__
from e3cli.commands.assignments import app as assignments_app
from e3cli.commands.courses import app as courses_app
from e3cli.commands.download import app as download_app
from e3cli.commands.login import app as login_app
from e3cli.commands.logout import app as logout_app
from e3cli.commands.schedule import app as schedule_app
from e3cli.commands.setup import app as setup_app
from e3cli.commands.setup import is_first_run, run_setup_wizard
from e3cli.commands.submit import app as submit_app
from e3cli.commands.sync import app as sync_app
from e3cli.i18n import t

app = typer.Typer(
    name="e3cli",
    help=t("cli.help"),
    no_args_is_help=True,
)

app.add_typer(login_app, name="login", help=t("cli.login"))
app.add_typer(logout_app, name="logout", help=t("cli.logout"))
app.add_typer(courses_app, name="courses", help=t("cli.courses"))
app.add_typer(assignments_app, name="assignments", help=t("cli.assignments"))
app.add_typer(download_app, name="download", help=t("cli.download"))
app.add_typer(submit_app, name="submit", help=t("cli.submit"))
app.add_typer(sync_app, name="sync", help=t("cli.sync"))
app.add_typer(schedule_app, name="schedule", help=t("cli.schedule"))
app.add_typer(setup_app, name="setup", help=t("cli.setup"))


@app.command()
def version():
    """Show version."""
    typer.echo(f"e3cli {__version__}")


_original_app_call = app.__call__


def _app_with_first_run(*args, **kwargs):
    skip_keywords = {"--help", "-h", "version", "setup", "--show-completion", "--install-completion"}
    if (
        is_first_run()
        and sys.stdin.isatty()
        and not any(arg in skip_keywords for arg in sys.argv[1:])
    ):
        run_setup_wizard()
        if len(sys.argv) <= 1:
            return
    return _original_app_call(*args, **kwargs)


app.__call__ = _app_with_first_run
