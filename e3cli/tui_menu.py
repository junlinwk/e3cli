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

import re
import sys
import tty
import termios
from dataclasses import dataclass

from rich.console import Console

console = Console()

# 用於計算上次渲染了多少行，以便正確覆蓋
_last_render_lines: int = 0


def _strip_rich_markup(text: str) -> str:
    """移除 rich markup tags，保留純文字。"""
    return re.sub(r"\[/?[a-z_ ]+\]", "", text)


@dataclass
class MenuItem:
    label: str
    key: str = ""
    description: str = ""
    disabled: bool = False


class MenuResult:
    """選單結果。"""

    def __init__(self, action: str, index: int = -1, key: str = "", cursor: int = 0):
        self.action = action  # "select", "back", "quit", "search"
        self.index = index
        self.key = key
        self.cursor = cursor  # 最後的 cursor 位置，供下次恢復


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
    """
    global _last_render_lines

    if not items:
        return MenuResult("back")

    cursor = max(0, min(selected, len(items) - 1))
    search_mode = False
    search_text = ""

    # 跳過 disabled items
    while 0 <= cursor < len(items) and items[cursor].disabled:
        cursor += 1
    if cursor >= len(items):
        cursor = 0

    while True:
        # 計算過濾後的項目
        if search_mode and search_text:
            query = search_text.lower()
            visible = [
                (i, item)
                for i, item in enumerate(items)
                if query in _strip_rich_markup(item.label).lower()
                or query in _strip_rich_markup(item.description).lower()
                or item.disabled
            ]  # 保留分組標題
        else:
            visible = list(enumerate(items))

        # 確保 cursor 在範圍內且不在 disabled 上
        if visible:
            cursor = cursor % len(visible)
            # 跳過 disabled
            attempts = 0
            while visible[cursor][1].disabled and attempts < len(visible):
                cursor = (cursor + 1) % len(visible)
                attempts += 1

        # 繪製
        _render_menu(visible, cursor, title, subtitle, search_mode, search_text)

        # 讀取輸入
        key = _read_key()

        if key == "up":
            if visible:
                cursor = (cursor - 1) % len(visible)
                while visible[cursor][1].disabled:
                    cursor = (cursor - 1) % len(visible)
        elif key == "down":
            if visible:
                cursor = (cursor + 1) % len(visible)
                while visible[cursor][1].disabled:
                    cursor = (cursor + 1) % len(visible)
        elif key in ("enter", "right"):
            if visible and 0 <= cursor < len(visible):
                real_idx = visible[cursor][0]
                if not items[real_idx].disabled:
                    _clear_render()
                    return MenuResult(
                        "select", real_idx, items[real_idx].key, cursor=cursor
                    )
        elif key in ("left", "esc"):
            if search_mode:
                search_mode = False
                search_text = ""
                cursor = 0
            else:
                _clear_render()
                return MenuResult("back", cursor=cursor)
        elif key in ("q",) and not search_mode:
            _clear_render()
            return MenuResult("back", cursor=cursor)
        elif key == "quit":
            _clear_render()
            return MenuResult("quit", cursor=cursor)
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
        elif not search_mode and len(key) == 1 and key.isprintable() and search_enabled:
            search_mode = True
            search_text = key
            cursor = 0


def _clear_render():
    """清除上次渲染的內容。"""
    global _last_render_lines
    if _last_render_lines > 0:
        sys.stdout.write(f"\033[{_last_render_lines}A\033[J")
        sys.stdout.flush()
        _last_render_lines = 0


def _render_menu(
    visible: list[tuple[int, MenuItem]],
    cursor: int,
    title: str,
    subtitle: str,
    search_mode: bool,
    search_text: str,
):
    """繪製選單到終端。"""
    global _last_render_lines

    width = min(console.width, 80)
    line_char = "─"
    output = []

    # 上分隔線
    if title:
        clean_title = _strip_rich_markup(title)
        pad = max(0, width - len(clean_title) - 4)
        left_pad = pad // 2
        right_pad = pad - left_pad
        output.append(
            f"\033[36m{line_char * left_pad} {clean_title} {line_char * right_pad}\033[0m"
        )
    else:
        output.append(f"\033[36m{line_char * width}\033[0m")

    if subtitle:
        clean_sub = _strip_rich_markup(subtitle)
        output.append(f"\033[2m  {clean_sub}\033[0m")

    output.append("")

    # 選項
    for vi, (real_idx, item) in enumerate(visible):
        is_selected = vi == cursor
        clean_label = _strip_rich_markup(item.label)
        clean_desc = _strip_rich_markup(item.description)

        if item.disabled:
            output.append(f"\033[2m  {clean_label}\033[0m")
        elif is_selected:
            # 整行反白（label + description 都包在 \033[7m 內）
            full = f"❯ {clean_label}"
            if clean_desc:
                full += f"  {clean_desc}"
            # 用空白填滿到 width，讓反白整行
            padded = full.ljust(width)
            output.append(f"\033[7m\033[36m{padded}\033[0m")
        else:
            # description 用較亮的顏色（白色 dim 而非深灰）
            desc_part = f"  \033[37m{clean_desc}\033[0m" if clean_desc else ""
            output.append(f"  \033[1m{clean_label}\033[0m{desc_part}")

    output.append("")

    # 搜尋列 / 操作提示
    if search_mode:
        output.append(f"\033[33m/ {search_text}\033[0m\033[5m▊\033[0m")
    else:
        output.append(
            "\033[2m↑↓ navigate  →/Enter select  ← back  / search  q quit\033[0m"
        )

    # 下分隔線
    output.append(f"\033[36m{line_char * width}\033[0m")

    # 先清除上次渲染，再重新繪製
    if _last_render_lines > 0:
        sys.stdout.write(f"\033[{_last_render_lines}A\033[J")

    rendered = "\n".join(output) + "\n"
    sys.stdout.write(rendered)
    sys.stdout.flush()

    _last_render_lines = len(output)


def wait_for_back(prompt_text: str = "") -> None:
    """等待使用者按 Enter、← 或 q 返回。支援方向鍵。"""
    if prompt_text:
        sys.stdout.write(f"\033[2m{prompt_text}\033[0m")
        sys.stdout.flush()
    else:
        sys.stdout.write("\033[2mEnter/← to go back\033[0m")
        sys.stdout.flush()

    while True:
        key = _read_key()
        if key in ("enter", "left", "q", "esc", "quit"):
            # 清除提示行
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            return


def show_menu_fullscreen(
    items: list[MenuItem],
    title: str = "",
    subtitle: str = "",
    search_enabled: bool = True,
    selected: int = 0,
) -> MenuResult:
    """
    全螢幕版選單 — 先印足夠空行再開始，避免覆蓋既有內容。
    """
    global _last_render_lines
    _last_render_lines = 0

    # 預留空間
    needed = len(items) + 8
    sys.stdout.write("\n" * needed)
    # 往回移，讓第一次 render 從正確位置開始
    sys.stdout.write(f"\033[{needed}A")
    sys.stdout.flush()
    _last_render_lines = needed

    return show_menu(
        items, title, subtitle, selected=selected, search_enabled=search_enabled
    )
