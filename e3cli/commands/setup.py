"""e3cli setup — interactive setup wizard."""

from __future__ import annotations

import getpass
import os

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from e3cli import __version__
from e3cli.auth import AuthError, get_token
from e3cli.config import CONFIG_FILE, ensure_dirs, save_token
from e3cli.credential import save_credentials
from e3cli.i18n import set_lang, t

console = Console()
app = typer.Typer()

BANNER = r"""
    _____ ____   _____ _      _____
   / ____|___ \ / ____| |    |_   _|
  | |__    __) | |    | |      | |
  |  __|  |__ <| |    | |      | |
  | |____ ___) | |____| |____ _| |_
  |______|____/ \_____|______|_____|
"""


def is_first_run() -> bool:
    return not CONFIG_FILE.exists()


def _choose_language() -> str:
    """讓使用者選擇語言 / Let user choose language."""
    console.print("[bold cyan]Language / 語言[/bold cyan]")
    console.print("  [cyan]1[/cyan] 繁體中文")
    console.print("  [cyan]2[/cyan] English")
    choice = typer.prompt("Choose / 請選擇", default="1", show_default=True)
    if choice.strip() in ("2", "en", "EN", "english", "English"):
        return "en"
    return "zh"


def run_setup_wizard() -> None:
    console.print()
    console.print(Panel(
        Text(BANNER, style="cyan", justify="center"),
        title=f"[bold]Welcome to e3cli v{__version__}[/bold]",
        subtitle="NYCU E3 Moodle automation tool",
        border_style="cyan",
    ))
    console.print()

    # Step 0: Language
    lang = _choose_language()
    set_lang(lang)
    console.print()

    console.print(f"[bold]{t('setup.welcome')}[/bold]")
    console.print()

    # Step 1: Moodle URL
    console.print(f"[bold cyan]Step 1/4[/bold cyan] — {t('setup.step_url')}")
    console.print(f"[dim]{t('setup.step_url_hint')}[/dim]")
    url = typer.prompt(
        "Moodle URL",
        default="https://e3p.nycu.edu.tw",
        show_default=True,
    ).rstrip("/")
    console.print()

    # Step 2: Download directory
    console.print(f"[bold cyan]Step 2/4[/bold cyan] — {t('setup.step_dir')}")
    console.print(f"[dim]{t('setup.step_dir_hint')}[/dim]")
    default_dir = os.path.expanduser("~/e3-downloads")
    download_dir = typer.prompt(
        t("setup.step_dir"),
        default=default_dir,
        show_default=True,
    )
    console.print()

    # Step 3: Save config (including language preference)
    console.print(f"[bold cyan]Step 3/4[/bold cyan] — {t('setup.step_save')}")
    ensure_dirs()
    config_content = f"""[moodle]
url = "{url}"
service = "moodle_mobile_app"

[storage]
download_dir = "{download_dir}"

[schedule]
interval_minutes = 60
notify = true

[general]
lang = "{lang}"
"""
    CONFIG_FILE.write_text(config_content)
    console.print(f"[green]  {t('setup.config_saved', path=CONFIG_FILE)}[/green]")
    console.print()

    # Step 4: Login
    console.print(f"[bold cyan]Step 4/4[/bold cyan] — {t('setup.step_login')}")
    want_login = typer.confirm(t("setup.want_login"), default=True)

    if want_login:
        username = typer.prompt(f"  {t('setup.prompt_id')}")
        password = getpass.getpass(f"  {t('login.prompt_pass')}")

        console.print(f"[dim]  {t('login.connecting', url=url)}[/dim]")
        try:
            token = get_token(url, username, password)
            save_token(token)

            save_creds = typer.confirm(f"  {t('setup.want_save_creds')}", default=True)
            if save_creds:
                save_credentials(username, password)
                console.print(f"[green]  {t('login.success_saved')}[/green]")
            else:
                console.print(f"[green]  {t('login.success')}[/green]")
        except AuthError as e:
            console.print(f"[red]  ✗ {e}[/red]")
            console.print(f"[dim]  {t('setup.login_fail_hint')}[/dim]")
    console.print()

    # Done
    console.print(Panel(
        f"[bold green]{t('setup.done_title')}[/bold green]\n\n{t('setup.done_body')}",
        title="[bold]Ready![/bold]",
        border_style="green",
    ))


@app.callback(invoke_without_command=True)
def setup():
    """Re-run interactive setup wizard."""
    run_setup_wizard()
