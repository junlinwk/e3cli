"""e3cli login"""

from __future__ import annotations

import getpass

import typer
from rich.console import Console

from e3cli.auth import AuthError, get_token
from e3cli.config import load_config, save_token
from e3cli.credential import has_credentials, load_credentials, save_credentials
from e3cli.i18n import t

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def login(
    username: str = typer.Option(None, "--username", "-u", help=t("login.opt_username")),
    save_password: bool = typer.Option(False, "--save", "-s", help=t("login.opt_save")),
    refresh: bool = typer.Option(False, "--refresh", "-r", help=t("login.opt_refresh")),
):
    """Login to NYCU E3 Moodle and save token."""
    cfg = load_config()

    if refresh:
        creds = load_credentials()
        if not creds:
            console.print(f"[red]{t('login.no_saved')}[/red]")
            raise typer.Exit(1)
        username, password = creds
        console.print(f"[dim]{t('login.refreshing', user=username)}[/dim]")
    else:
        if not username and has_credentials():
            creds = load_credentials()
            if creds:
                use_saved = typer.confirm(t("login.use_saved", user=creds[0]), default=True)
                if use_saved:
                    username, password = creds
                else:
                    username = typer.prompt(t("login.prompt_user"))
                    password = getpass.getpass(t("login.prompt_pass"))
            else:
                username = typer.prompt(t("login.prompt_user"))
                password = getpass.getpass(t("login.prompt_pass"))
        else:
            if not username:
                username = typer.prompt(t("login.prompt_user"))
            password = getpass.getpass(t("login.prompt_pass"))

    console.print(f"[dim]{t('login.connecting', url=cfg.moodle.url)}[/dim]")

    try:
        token = get_token(cfg.moodle.url, username, password, cfg.moodle.service)
    except AuthError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)

    save_token(token)

    if save_password or refresh:
        save_credentials(username, password)
        console.print(f"[green]{t('login.success_saved')}[/green]")
    else:
        console.print(f"[green]{t('login.success')}[/green]")
        console.print(f"[dim]{t('login.hint_save')}[/dim]")
