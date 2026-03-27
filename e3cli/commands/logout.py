"""e3cli logout"""

from __future__ import annotations

import typer
from rich.console import Console

from e3cli.credential import clear_credentials
from e3cli.i18n import t

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def logout():
    """Clear all stored credentials and tokens."""
    clear_credentials()
    console.print(f"[green]{t('logout.done')}[/green]")
