"""e3cli message — 發送站內訊息。"""

from __future__ import annotations

import typer
from rich.console import Console

from e3cli.api.messages import send_message
from e3cli.commands._common import get_client
from e3cli.i18n import t

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def message(
    to: int = typer.Argument(..., help=t("msg.opt_to")),
    text: str = typer.Argument(None, help=t("msg.opt_text")),
):
    """Send a message to a Moodle user."""
    client = get_client()

    # 如果沒有提供文字，互動式輸入
    if not text:
        console.print(f"[dim]{t('msg.content_prompt')}[/dim]")
        lines = []
        while True:
            try:
                line = input()
                if line == "":
                    break
                lines.append(line)
            except (EOFError, KeyboardInterrupt):
                break
        text = "\n".join(lines)

    if not text.strip():
        console.print(f"[dim]{t('msg.cancelled')}[/dim]")
        raise typer.Exit()

    # 確認
    console.print(f"\n[dim]{t('msg.to', name=str(to))}[/dim]")
    console.print("[dim]───[/dim]")
    console.print(text)
    console.print("[dim]───[/dim]")
    confirm = typer.confirm(t("msg.confirm"), default=True)

    if not confirm:
        console.print(f"[dim]{t('msg.cancelled')}[/dim]")
        raise typer.Exit()

    try:
        result = send_message(client, to, text)
        # 檢查回傳
        if result and isinstance(result, list):
            err = result[0].get("errormessage", "")
            if err:
                console.print(f"[red]{t('msg.failed', e=err)}[/red]")
            else:
                console.print(f"[green]{t('msg.sent')}[/green]")
        else:
            console.print(f"[green]{t('msg.sent')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('msg.failed', e=str(e))}[/red]")
