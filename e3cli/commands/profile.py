"""e3cli profile — 管理多帳號。"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from e3cli.credential import activate_profile, clear_credentials, get_active_profile, list_profiles
from e3cli.i18n import t

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def profile_list():
    """List all profiles and show active one."""
    profiles = list_profiles()

    if not profiles:
        console.print(f"[dim]{t('profile.empty')}[/dim]")
        return

    table = Table(title=t("profile.title"))
    table.add_column("", width=3)
    table.add_column(t("profile.col_name"), style="bold")
    table.add_column(t("profile.col_user"))
    table.add_column(t("profile.col_url"), style="dim")

    for p in profiles:
        marker = "[green]●[/green]" if p["active"] else " "
        name_style = "bold green" if p["active"] else ""
        url_display = p.get("moodle_url", "").replace("https://", "").replace("http://", "")
        table.add_row(
            marker,
            f"[{name_style}]{p['name']}[/{name_style}]" if name_style else p["name"],
            p["username"],
            url_display,
        )

    console.print(table)
    console.print(f"[dim]{t('profile.active', name=get_active_profile())}[/dim]")


@app.command("use")
def profile_use(
    name: str = typer.Argument(..., help="Profile name to switch to"),
):
    """Switch active profile."""
    if activate_profile(name):
        console.print(f"[green]{t('profile.switched', name=name)}[/green]")
    else:
        console.print(f"[red]{t('profile.not_found', name=name)}[/red]")
        profiles = list_profiles()
        if profiles:
            names = ", ".join(p["name"] for p in profiles)
            console.print(f"[dim]{t('profile.available')}: {names}[/dim]")


@app.command("remove")
def profile_remove(
    name: str = typer.Argument(..., help="Profile name to remove"),
):
    """Remove a profile and its credentials."""
    confirm = typer.confirm(t("profile.confirm_remove", name=name), default=False)
    if confirm:
        clear_credentials(name)
        console.print(f"[green]{t('profile.removed', name=name)}[/green]")
