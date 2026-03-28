"""共用格式化工具。"""

from __future__ import annotations

import time
from datetime import datetime

from e3cli.i18n import t


def format_duedate(ts: int, use_rich: bool = True) -> str:
    """
    格式化截止日期，根據剩餘時間漸變顏色。

    顏色邏輯（rich markup）：
      已過期      → 深紅 (bold red)
      0-1 天      → 紅色 (red)
      1-3 天      → 橘紅 (dark_orange)
      3-5 天      → 橘色 (orange3)
      5-7 天      → 黃色 (yellow)
      7-14 天     → 淺黃 (khaki1)
      14+ 天      → 無色
    """
    if ts == 0:
        return t("assign.no_deadline")

    dt = datetime.fromtimestamp(ts)
    remaining = ts - int(time.time())
    days = remaining // 86400

    date_str = f"{dt:%Y-%m-%d %H:%M}"

    if not use_rich:
        if remaining < 0:
            return f"{date_str} ({t('assign.expired')})"
        return f"{date_str} ({t('assign.days_left', n=days)})"

    if remaining < 0:
        return f"[bold red]{date_str} ({t('assign.expired')})[/bold red]"
    if days < 1:
        hours = remaining // 3600
        return f"[red]{date_str} ({hours}h)[/red]"
    if days <= 3:
        return f"[dark_orange]{date_str} ({t('assign.days_left', n=days)})[/dark_orange]"
    if days <= 5:
        return f"[orange3]{date_str} ({t('assign.days_left', n=days)})[/orange3]"
    if days <= 7:
        return f"[yellow]{date_str} ({t('assign.days_left', n=days)})[/yellow]"
    if days <= 14:
        return f"[khaki1]{date_str} ({t('assign.days_left', n=days)})[/khaki1]"
    return f"{date_str} ({t('assign.days_left', n=days)})"


def format_submission_status(status: str) -> str:
    """
    格式化提交狀態，已繳交綠色標注。

    Moodle 狀態值：
      "submitted"  → 綠色 ✓ 已繳交
      "draft"      → 黃色 草稿
      "new"        → 灰色 未繳交
      "reopened"   → 橘色 重新開放
    """
    status_map = {
        "submitted": "[bold green]✓ {label}[/bold green]",
        "draft": "[yellow]✎ {label}[/yellow]",
        "new": "[dim]— {label}[/dim]",
        "reopened": "[orange3]↻ {label}[/orange3]",
        "unknown": "[dim]? —[/dim]",
    }
    label_map = {
        "submitted": t("assign.submitted"),
        "draft": t("assign.draft_status"),
        "new": t("assign.not_submitted"),
        "reopened": t("assign.reopened"),
        "unknown": "—",
    }
    template = status_map.get(status, "[dim]{label}[/dim]")
    label = label_map.get(status, status)
    return template.format(label=label)


def sort_assignments(items: list[tuple], now: int | None = None) -> list[tuple]:
    """
    排序作業列表。每個 item 是 (assignment_dict, status_str, ...其他欄位)。

    排序規則（由上到下）：
      1. 未繳交 + 未過期 → 越接近 deadline 越上面
      2. 已過期（未繳交）→ 越接近現在越上面
      3. 已繳交           → 越新繳交的越上面

    status 在 item[1], duedate 從 item[0]["duedate"] 取。
    """
    if now is None:
        now = int(time.time())

    def _sort_key(item):
        assign = item[0]
        status = item[1]
        duedate = assign.get("duedate", 0)

        if status == "submitted":
            # 已繳交：排最下面 (group=2)，越新的越上面（duedate 大的排前）
            return (2, -(duedate or 0))
        elif duedate > 0 and duedate < now:
            # 已過期未繳交：中間 (group=1)，越接近現在越上面（duedate 大的排前）
            return (1, -duedate)
        else:
            # 未繳交未過期：最上面 (group=0)，越接近 deadline 越上面（duedate 小的排前）
            # duedate=0 (無截止日) 排在這組最下面
            return (0, duedate if duedate > 0 else float("inf"))

    return sorted(items, key=_sort_key)
