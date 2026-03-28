"""
方向鍵互動式選單 — 跨平台（Linux/macOS）。

支援：
  ↑/↓  移動選取
  ←    返回上一層
  →/Enter  進入選項
  /    搜尋模式
  q    離開

視覺風格仿 Claude Code CLI：上下分隔線 + 反白當前選項。
"""

from __future__ import annotations

import sys
import tty
import termios
from dataclasses import dataclass

from rich.console import Console

console = Console()


@dataclass
class MenuItem:
    label: str
    key: str = ""
    description: str = ""
    disabled: bool = False


class MenuResult:
    """選單結果。"""
    def __init__(self, action: str, index: int = -1, key: str = ""):
        self.action = action   # "select", "back", "quit", "search"
        self.index = index
        self.key = key


def _read_key() -> str:
    """讀取單一按鍵（含方向鍵）。跨平台 Linux/macOS。"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            seq = sys.stdin.read(2)
            if seq == "[A":
                return "up"
            if seq == "[B":
                return "down"
            if seq == "[C":
                return "right"
            if seq == "[D":
                return "left"
            return "esc"
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x03":  # Ctrl+C
            return "quit"
        if ch == "\x7f" or ch == "\x08":  # Backspace
            return "backspace"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def show_menu(
    items: list[MenuItem],
    title: str = "",
    subtitle: str = "",
    selected: int = 0,
    search_enabled: bool = True,
) -> MenuResult:
    """
    顯示互動式選單，支援方向鍵導航。

    回傳 MenuResult:
      action="select" + index: 使用者選了某個項目
      action="back": 使用者按 ← 或 q
      action="quit": 使用者按 Ctrl+C
      action="search" + key: 使用者開始輸入搜尋
    """
    if not items:
        return MenuResult("back")

    cursor = max(0, min(selected, len(items) - 1))
    search_mode = False
    search_text = ""

    while True:
        # 計算過濾後的項目
        if search_mode and search_text:
            query = search_text.lower()
            visible = [(i, item) for i, item in enumerate(items)
                       if query in item.label.lower() or query in item.description.lower()]
        else:
            visible = list(enumerate(items))

        # 繪製
        _render_menu(visible, cursor, title, subtitle, search_mode, search_text)

        # 讀取輸入
        key = _read_key()

        if key == "up":
            cursor = (cursor - 1) % len(visible) if visible else 0
        elif key == "down":
            cursor = (cursor + 1) % len(visible) if visible else 0
        elif key in ("enter", "right"):
            if visible and 0 <= cursor < len(visible):
                real_idx = visible[cursor][0]
                if not items[real_idx].disabled:
                    return MenuResult("select", real_idx, items[real_idx].key)
        elif key in ("left", "esc"):
            if search_mode:
                search_mode = False
                search_text = ""
                cursor = 0
            else:
                return MenuResult("back")
        elif key in ("q",) and not search_mode:
            return MenuResult("back")
        elif key == "quit":
            return MenuResult("quit")
        elif key == "/" and not search_mode and search_enabled:
            search_mode = True
            search_text = ""
            cursor = 0
        elif key == "backspace" and search_mode:
            search_text = search_text[:-1]
            cursor = 0
            if not search_text:
                search_mode = False
        elif search_mode and len(key) == 1 and key.isprintable():
            search_text += key
            cursor = 0
        elif not search_mode and len(key) == 1 and key.isprintable():
            # 直接開始搜尋
            if search_enabled:
                search_mode = True
                search_text = key
                cursor = 0


def _render_menu(
    visible: list[tuple[int, MenuItem]],
    cursor: int,
    title: str,
    subtitle: str,
    search_mode: bool,
    search_text: str,
):
    """繪製選單到終端。"""
    # 取得終端寬度
    width = console.width

    # 清屏（移到最上方）
    output = []

    # 上分隔線
    line_char = "─"
    if title:
        pad = max(0, width - len(title) - 4)
        left_pad = pad // 2
        right_pad = pad - left_pad
        output.append(f"\033[36m{line_char * left_pad} {title} {line_char * right_pad}\033[0m")
    else:
        output.append(f"\033[36m{line_char * width}\033[0m")

    if subtitle:
        output.append(f"\033[2m  {subtitle}\033[0m")

    output.append("")

    # 選項
    for vi, (real_idx, item) in enumerate(visible):
        is_selected = vi == cursor
        prefix = "❯ " if is_selected else "  "
        label = item.label
        desc = f"  \033[2m{item.description}\033[0m" if item.description else ""

        if is_selected:
            # 反白
            output.append(f"\033[7m\033[36m{prefix}{label}\033[0m{desc}")
        elif item.disabled:
            output.append(f"\033[2m{prefix}{label}{desc}\033[0m")
        else:
            output.append(f"{prefix}{label}{desc}")

    output.append("")

    # 搜尋列
    if search_mode:
        output.append(f"\033[33m/ {search_text}\033[0m\033[5m▊\033[0m")
    else:
        hints = "\033[2m↑↓ navigate  →/Enter select  ← back  / search  q quit\033[0m"
        output.append(hints)

    # 下分隔線
    output.append(f"\033[36m{line_char * width}\033[0m")

    # 輸出（先清屏再繪製）
    total_lines = len(output)
    sys.stdout.write(f"\033[{total_lines + 2}A\033[J")  # 往上移並清除
    sys.stdout.write("\n".join(output) + "\n")
    sys.stdout.flush()


def show_menu_fullscreen(
    items: list[MenuItem],
    title: str = "",
    subtitle: str = "",
    search_enabled: bool = True,
) -> MenuResult:
    """
    全螢幕版選單 — 先印足夠空行再開始，避免覆蓋既有內容。
    """
    # 預留空間
    needed = len(items) + 8
    sys.stdout.write("\n" * needed)
    sys.stdout.flush()

    return show_menu(items, title, subtitle, search_enabled=search_enabled)
