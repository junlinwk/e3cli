"""設定管理 — 讀取/寫入 ~/.e3cli/config.toml"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("E3CLI_CONFIG_DIR", str(Path.home() / ".e3cli")))
CONFIG_FILE = CONFIG_DIR / "config.toml"
TOKEN_FILE = CONFIG_DIR / "token"
DB_PATH = CONFIG_DIR / "data" / "e3cli.db"
DEFAULT_DOWNLOAD_DIR = Path(os.environ.get("E3CLI_DOWNLOAD_DIR", str(Path.home() / "e3-downloads")))


@dataclass
class MoodleConfig:
    url: str = "https://e3p.nycu.edu.tw"
    service: str = "moodle_mobile_app"


@dataclass
class StorageConfig:
    download_dir: Path = field(default_factory=lambda: DEFAULT_DOWNLOAD_DIR)
    db_path: Path = field(default_factory=lambda: DB_PATH)


@dataclass
class ScheduleConfig:
    interval_minutes: int = 60
    notify: bool = True


@dataclass
class GeneralConfig:
    lang: str = ""                   # "" = auto-detect, "zh", "en"
    semester_format: str = "nycu"    # "nycu", "ntu", "western", "none", or custom regex
    alias: str = ""                  # custom command alias (e.g. "moodle")


@dataclass
class Config:
    moodle: MoodleConfig = field(default_factory=MoodleConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    general: GeneralConfig = field(default_factory=GeneralConfig)


def ensure_dirs() -> None:
    """建立必要的目錄。"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "data").mkdir(exist_ok=True)


def load_config() -> Config:
    """從 ~/.e3cli/config.toml 載入設定，不存在則使用預設值。"""
    ensure_dirs()
    cfg = Config()

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)

        if "moodle" in data:
            m = data["moodle"]
            cfg.moodle.url = m.get("url", cfg.moodle.url)
            cfg.moodle.service = m.get("service", cfg.moodle.service)

        if "storage" in data:
            s = data["storage"]
            if "download_dir" in s:
                cfg.storage.download_dir = Path(os.path.expanduser(s["download_dir"]))
            if "db_path" in s:
                cfg.storage.db_path = Path(os.path.expanduser(s["db_path"]))

        if "schedule" in data:
            sc = data["schedule"]
            cfg.schedule.interval_minutes = sc.get("interval_minutes", cfg.schedule.interval_minutes)
            cfg.schedule.notify = sc.get("notify", cfg.schedule.notify)

        if "general" in data:
            g = data["general"]
            cfg.general.lang = g.get("lang", cfg.general.lang)
            cfg.general.semester_format = g.get("semester_format", cfg.general.semester_format)
            cfg.general.alias = g.get("alias", cfg.general.alias)

    # 套用學期格式
    from e3cli.semester import set_semester_format
    set_semester_format(cfg.general.semester_format)

    # 依據 active profile 名稱建立子目錄
    from e3cli.credential import get_active_profile
    profile_name = get_active_profile()
    cfg.storage.download_dir = cfg.storage.download_dir / profile_name

    return cfg


def save_token(token: str) -> None:
    """儲存 token 到 ~/.e3cli/token (chmod 600)。"""
    ensure_dirs()
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)


def load_token() -> str | None:
    """讀取已儲存的 token，不存在則回傳 None。"""
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return None
