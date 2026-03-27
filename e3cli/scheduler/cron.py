"""Crontab 排程管理。"""

from __future__ import annotations

import shutil
import subprocess
import sys

CRON_MARKER = "# e3cli-sync"


def _get_e3cli_cmd() -> str:
    """取得 e3cli 的完整路徑。"""
    path = shutil.which("e3cli")
    if path:
        return path
    return f"{sys.executable} -m e3cli"


def _get_current_crontab() -> list[str]:
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.strip().split("\n") if line]


def install(interval_minutes: int = 60) -> None:
    """安裝 cron job 定時執行 e3cli sync。"""
    lines = [entry for entry in _get_current_crontab() if CRON_MARKER not in entry]
    cmd = _get_e3cli_cmd()
    lines.append(f"*/{interval_minutes} * * * * {cmd} sync --quiet {CRON_MARKER}")
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)


def uninstall() -> None:
    """移除 e3cli 的 cron job。"""
    lines = [entry for entry in _get_current_crontab() if CRON_MARKER not in entry]
    if lines:
        subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)
    else:
        subprocess.run(["crontab", "-r"], capture_output=True)


def is_installed() -> bool:
    """檢查 cron job 是否已安裝。"""
    return any(CRON_MARKER in entry for entry in _get_current_crontab())


def get_schedule_line() -> str | None:
    """取得目前的排程設定行。"""
    for entry in _get_current_crontab():
        if CRON_MARKER in entry:
            return entry
    return None
