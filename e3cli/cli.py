"""E3CLI 主入口 — 組裝所有子指令。"""

from __future__ import annotations

import typer

from e3cli import __version__
from e3cli.commands.assignments import app as assignments_app
from e3cli.commands.courses import app as courses_app
from e3cli.commands.download import app as download_app
from e3cli.commands.login import app as login_app
from e3cli.commands.logout import app as logout_app
from e3cli.commands.schedule import app as schedule_app
from e3cli.commands.submit import app as submit_app
from e3cli.commands.sync import app as sync_app

app = typer.Typer(
    name="e3cli",
    help="NYCU E3 Moodle 自動化工具",
    no_args_is_help=True,
)

app.add_typer(login_app, name="login", help="登入取得 token")
app.add_typer(logout_app, name="logout", help="清除認證資料")
app.add_typer(courses_app, name="courses", help="列出修課清單")
app.add_typer(assignments_app, name="assignments", help="列出作業與截止日期")
app.add_typer(download_app, name="download", help="下載課程教材")
app.add_typer(submit_app, name="submit", help="提交作業")
app.add_typer(sync_app, name="sync", help="全量同步")
app.add_typer(schedule_app, name="schedule", help="管理定時同步排程")


@app.command()
def version():
    """顯示版本。"""
    typer.echo(f"e3cli {__version__}")
