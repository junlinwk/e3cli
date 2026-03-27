"""e3cli login — 登入取得 token，可選擇記住帳密。"""

from __future__ import annotations

import getpass

import typer
from rich.console import Console

from e3cli.auth import AuthError, get_token
from e3cli.config import load_config, save_token
from e3cli.credential import has_credentials, load_credentials, save_credentials

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def login(
    username: str = typer.Option(None, "--username", "-u", help="學號/帳號"),
    save_password: bool = typer.Option(False, "--save", "-s", help="加密儲存帳密，下次自動登入"),
    refresh: bool = typer.Option(False, "--refresh", "-r", help="使用已儲存的帳密重新取得 token"),
):
    """登入 NYCU E3 Moodle 並儲存 token。"""
    cfg = load_config()

    # --refresh: 用已儲存的帳密自動登入
    if refresh:
        creds = load_credentials()
        if not creds:
            console.print("[red]找不到已儲存的帳密，請先用 e3cli login --save 登入。[/red]")
            raise typer.Exit(1)
        username, password = creds
        console.print(f"[dim]使用已儲存的帳密重新取得 token ({username}) ...[/dim]")
    else:
        # 如果有儲存的帳密且沒有指定 username，提示是否使用
        if not username and has_credentials():
            creds = load_credentials()
            if creds:
                use_saved = typer.confirm(f"使用已儲存的帳號 ({creds[0]}) 登入？", default=True)
                if use_saved:
                    username, password = creds
                else:
                    username = typer.prompt("帳號")
                    password = getpass.getpass("密碼: ")
            else:
                username = typer.prompt("帳號")
                password = getpass.getpass("密碼: ")
        else:
            if not username:
                username = typer.prompt("帳號")
            password = getpass.getpass("密碼: ")

    console.print(f"[dim]正在連線 {cfg.moodle.url} ...[/dim]")

    try:
        token = get_token(cfg.moodle.url, username, password, cfg.moodle.service)
    except AuthError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)

    save_token(token)

    # 儲存帳密
    if save_password or refresh:
        save_credentials(username, password)
        console.print("[green]✓ 登入成功！Token 已儲存，帳密已加密保存。[/green]")
    else:
        console.print("[green]✓ 登入成功！Token 已儲存。[/green]")
        console.print("[dim]提示: 加上 --save 可記住帳密，下次用 --refresh 自動重新登入。[/dim]")
