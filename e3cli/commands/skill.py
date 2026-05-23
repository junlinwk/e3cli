"""e3cli skill — install the e3cli SKILL.md into Claude Code / Codex / Gemini CLI."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer()

SKILL_NAME = "e3cli"


@dataclass(frozen=True)
class Target:
    name: str
    detect_dir: Path
    skill_path: Path
    extras: tuple[tuple[Path, str], ...] = ()


def _targets() -> list[Target]:
    home = Path.home()
    return [
        Target(
            name="claude",
            detect_dir=home / ".claude",
            skill_path=home / ".claude" / "skills" / SKILL_NAME / "SKILL.md",
        ),
        Target(
            name="codex",
            detect_dir=home / ".codex",
            skill_path=home / ".codex" / "skills" / SKILL_NAME / "SKILL.md",
        ),
        # Antigravity CLI (`agy`) — Gemini CLI's successor. Reads skills from
        # ~/.gemini/antigravity-cli/skills/. Standard SKILL.md format (our
        # bundled file already has the YAML frontmatter agy expects).
        Target(
            name="antigravity",
            detect_dir=home / ".gemini" / "antigravity-cli",
            skill_path=home / ".gemini" / "antigravity-cli" / "skills" / SKILL_NAME / "SKILL.md",
        ),
        # Legacy Gemini CLI extension format (kept for backward compat with
        # users still on the pre-agy Gemini CLI). Uses ~/.gemini/extensions/
        # with a gemini-extension.json descriptor.
        Target(
            name="gemini",
            detect_dir=home / ".gemini",
            skill_path=home / ".gemini" / "extensions" / SKILL_NAME / "skills" / SKILL_NAME / "SKILL.md",
            extras=(
                (
                    Path(".gemini") / "extensions" / SKILL_NAME / "gemini-extension.json",
                    json.dumps(
                        {
                            "name": SKILL_NAME,
                            "version": "0.1.0",
                            "description": "e3cli — Moodle automation skill",
                        },
                        indent=2,
                    )
                    + "\n",
                ),
            ),
        ),
    ]


def _bundled_skill_text() -> str:
    return (resources.files("e3cli") / "skills" / SKILL_NAME / "SKILL.md").read_text(
        encoding="utf-8"
    )


def _detected(targets: list[Target]) -> list[Target]:
    found = [t for t in targets if t.detect_dir.is_dir()]
    # 若同時偵測到 antigravity (agy) 和 legacy gemini，自動跳過 legacy gemini。
    # antigravity 的 detect_dir (~/.gemini/antigravity-cli) 是 gemini 的子目錄，
    # 沒這個排除的話會在新 agy 用戶機器上重複裝。
    names = {t.name for t in found}
    if "antigravity" in names and "gemini" in names:
        found = [t for t in found if t.name != "gemini"]
    return found


def _install_one(target: Target, content: str, force: bool) -> tuple[bool, str]:
    dest = target.skill_path
    if dest.exists() and not force:
        return False, f"already installed at {dest} (use --force to overwrite)"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    home = Path.home()
    for rel_path, body in target.extras:
        extra = home / rel_path
        extra.parent.mkdir(parents=True, exist_ok=True)
        if not extra.exists() or force:
            extra.write_text(body, encoding="utf-8")
    return True, f"installed → {dest}"


@app.callback(invoke_without_command=True)
def _default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        # Default to status when no subcommand given
        status()


@app.command("install")
def install(
    target: str = typer.Option(
        "auto",
        "--target",
        "-t",
        help="Which agent CLI to install for: auto | claude | codex | gemini | all",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing SKILL.md"),
):
    """Install the e3cli skill so AI coding agents know how to use this CLI."""
    all_targets = _targets()
    by_name = {t.name: t for t in all_targets}

    if target == "all":
        chosen = all_targets
    elif target == "auto":
        chosen = _detected(all_targets)
        if not chosen:
            console.print(
                "[yellow]No agent CLIs detected (~/.claude, ~/.codex, ~/.gemini all missing).[/yellow]"
            )
            console.print(
                "[dim]Install one of them first, or run with --target <name> to force install.[/dim]"
            )
            raise typer.Exit(code=1)
    else:
        if target not in by_name:
            console.print(f"[red]Unknown target: {target}[/red]")
            console.print(f"[dim]Valid: auto, all, {', '.join(by_name)}[/dim]")
            raise typer.Exit(code=1)
        chosen = [by_name[target]]

    content = _bundled_skill_text()
    for tg in chosen:
        ok, msg = _install_one(tg, content, force=force)
        marker = "[green]✓[/green]" if ok else "[yellow]·[/yellow]"
        console.print(f"  {marker} [bold]{tg.name}[/bold]: {msg}")


@app.command("uninstall")
def uninstall(
    target: str = typer.Option(
        "all",
        "--target",
        "-t",
        help="Which agent CLI to remove from: claude | codex | gemini | all",
    ),
):
    """Remove the e3cli skill from agent CLI directories."""
    all_targets = _targets()
    by_name = {t.name: t for t in all_targets}

    chosen = all_targets if target == "all" else [by_name.get(target)]
    if any(c is None for c in chosen):
        console.print(f"[red]Unknown target: {target}[/red]")
        raise typer.Exit(code=1)

    home = Path.home()
    for tg in chosen:
        skill_dir = tg.skill_path.parent
        if skill_dir.is_dir():
            shutil.rmtree(skill_dir)
            console.print(f"  [green]✓[/green] [bold]{tg.name}[/bold]: removed {skill_dir}")
        else:
            console.print(f"  [dim]·[/dim] [bold]{tg.name}[/bold]: nothing to remove")
        for rel_path, _ in tg.extras:
            extra = home / rel_path
            if extra.exists():
                extra.unlink()


@app.command("status")
def status():
    """Show which agent CLIs are detected and where the skill is installed."""
    table = Table(title="e3cli skill status")
    table.add_column("Agent", style="bold")
    table.add_column("Detected")
    table.add_column("Installed")
    table.add_column("Path", style="dim")

    for tg in _targets():
        detected = "[green]yes[/green]" if tg.detect_dir.is_dir() else "[dim]no[/dim]"
        installed = "[green]yes[/green]" if tg.skill_path.exists() else "[dim]no[/dim]"
        table.add_row(tg.name, detected, installed, str(tg.skill_path))

    console.print(table)
    console.print(
        "[dim]Run [bold]e3cli skill install[/bold] to install for all detected agents.[/dim]"
    )
