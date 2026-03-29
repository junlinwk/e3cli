"""
安全帳密儲存 — 支援多帳號 profile。

每個 profile 存在 ~/.e3cli/profiles/<name>/ 下：
  key               — 加密金鑰 (chmod 600)
  credentials.enc   — 加密帳密 (chmod 600)
  token             — Moodle API token (chmod 600)
  profile.json      — Profile 設定（moodle_url, service）

~/.e3cli/active_profile — 記錄當前預設 profile 名稱

向下相容：舊的單一帳號檔案（~/.e3cli/credentials.enc）會自動遷移為 "default" profile。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os

from e3cli.config import CONFIG_DIR, TOKEN_FILE, ensure_dirs

PROFILES_DIR = CONFIG_DIR / "profiles"
ACTIVE_FILE = CONFIG_DIR / "active_profile"

# 舊版單一帳號路徑（向下相容）
_LEGACY_KEY = CONFIG_DIR / "key"
_LEGACY_CRED = CONFIG_DIR / "credentials.enc"


def _profile_dir(name: str):
    d = PROFILES_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_or_create_key(profile: str) -> bytes:
    key_file = _profile_dir(profile) / "key"
    if key_file.exists():
        return key_file.read_bytes()
    key = os.urandom(32)
    key_file.write_bytes(key)
    key_file.chmod(0o600)
    return key


def _derive_key(master_key: bytes, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", master_key, salt, iterations=100_000)


def _xor_bytes(data: bytes, key_stream: bytes) -> bytes:
    return bytes(d ^ key_stream[i % len(key_stream)] for i, d in enumerate(data))


def _encrypt(plaintext: bytes, master_key: bytes) -> bytes:
    salt = os.urandom(16)
    derived = _derive_key(master_key, salt)
    ciphertext = _xor_bytes(plaintext, derived)
    mac = hmac.new(derived, ciphertext, hashlib.sha256).digest()
    return base64.b64encode(salt + mac + ciphertext)


def _decrypt(encoded: bytes, master_key: bytes) -> bytes | None:
    try:
        raw = base64.b64decode(encoded)
        if len(raw) < 48:
            return None
        salt, stored_mac, ciphertext = raw[:16], raw[16:48], raw[48:]
        derived = _derive_key(master_key, salt)
        expected_mac = hmac.new(derived, ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(stored_mac, expected_mac):
            return None
        return _xor_bytes(ciphertext, derived)
    except Exception:
        return None


# ─── Active profile ─────────────────────────────────────────────────────

def get_active_profile() -> str:
    """取得當前 active profile 名稱。"""
    ensure_dirs()
    _migrate_legacy()
    if ACTIVE_FILE.exists():
        name = ACTIVE_FILE.read_text().strip()
        if name and (_profile_dir(name) / "credentials.enc").exists():
            return name
    # 找第一個有 credentials 的 profile
    if PROFILES_DIR.exists():
        for d in sorted(PROFILES_DIR.iterdir()):
            if d.is_dir() and (d / "credentials.enc").exists():
                set_active_profile(d.name)
                return d.name
    return "default"


def set_active_profile(name: str) -> None:
    """設定 active profile。"""
    ensure_dirs()
    ACTIVE_FILE.write_text(name)


def list_profiles() -> list[dict]:
    """列出所有 profiles，回傳 [{"name", "username", "active", "moodle_url"}]。"""
    ensure_dirs()
    _migrate_legacy()
    active = get_active_profile()
    profiles = []
    if PROFILES_DIR.exists():
        for d in sorted(PROFILES_DIR.iterdir()):
            if d.is_dir() and (d / "credentials.enc").exists():
                creds = load_credentials(d.name)
                username = creds[0] if creds else "?"
                meta = load_profile_meta(d.name)
                profiles.append({
                    "name": d.name,
                    "username": username,
                    "active": d.name == active,
                    "moodle_url": meta.get("moodle_url", ""),
                })
    return profiles


# ─── Profile metadata ────────────────────────────────────────────────────

def save_profile_meta(profile: str, *, moodle_url: str = "", service: str = "moodle_mobile_app") -> None:
    """儲存 profile 的 Moodle 平台設定。"""
    meta_file = _profile_dir(profile) / "profile.json"
    meta = {}
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    if moodle_url:
        meta["moodle_url"] = moodle_url
    if service:
        meta["service"] = service
    meta_file.write_text(json.dumps(meta, ensure_ascii=False))


def load_profile_meta(profile: str | None = None) -> dict:
    """讀取 profile 的 Moodle 平台設定。回傳 {"moodle_url": str, "service": str}。"""
    if profile is None:
        profile = get_active_profile()
    meta_file = _profile_dir(profile) / "profile.json"
    if meta_file.exists():
        try:
            return json.loads(meta_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


# ─── Credential operations ───────────────────────────────────────────────

def save_credentials(username: str, password: str, profile: str | None = None) -> None:
    """加密儲存帳密到指定 profile。"""
    ensure_dirs()
    if profile is None:
        profile = get_active_profile()
    key = _get_or_create_key(profile)
    data = json.dumps({"username": username, "password": password}).encode()
    encrypted = _encrypt(data, key)
    cred_file = _profile_dir(profile) / "credentials.enc"
    cred_file.write_bytes(encrypted)
    cred_file.chmod(0o600)
    set_active_profile(profile)


def load_credentials(profile: str | None = None) -> tuple[str, str] | None:
    """讀取指定 profile 的帳密。"""
    if profile is None:
        profile = get_active_profile()
    pdir = _profile_dir(profile)
    cred_file = pdir / "credentials.enc"
    key_file = pdir / "key"
    if not cred_file.exists() or not key_file.exists():
        return None
    try:
        key = key_file.read_bytes()
        decrypted = _decrypt(cred_file.read_bytes(), key)
        if decrypted is None:
            return None
        data = json.loads(decrypted)
        return data["username"], data["password"]
    except (KeyError, json.JSONDecodeError):
        return None


def save_token_for_profile(token: str, profile: str | None = None) -> None:
    """儲存 token 到 profile 目錄，同時也存一份到主 token 位置。"""
    if profile is None:
        profile = get_active_profile()
    token_file = _profile_dir(profile) / "token"
    token_file.write_text(token)
    token_file.chmod(0o600)
    # 同步到主 token（供 API client 使用）
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)


def activate_profile(name: str) -> bool:
    """切換到指定 profile，載入其 token 和 Moodle URL。回傳是否成功。"""
    pdir = _profile_dir(name)
    if not (pdir / "credentials.enc").exists():
        return False
    set_active_profile(name)
    # 載入此 profile 的 token
    token_file = pdir / "token"
    if token_file.exists():
        TOKEN_FILE.write_text(token_file.read_text())
        TOKEN_FILE.chmod(0o600)
    # 套用此 profile 的 Moodle URL 到 config
    meta = load_profile_meta(name)
    if meta.get("moodle_url"):
        _apply_profile_url(meta["moodle_url"], meta.get("service", "moodle_mobile_app"))
    return True


def _apply_profile_url(url: str, service: str = "moodle_mobile_app") -> None:
    """將 profile 的 Moodle URL 寫入 config.toml。"""
    import tomllib
    from e3cli.config import CONFIG_FILE
    if not CONFIG_FILE.exists():
        return
    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)
    data.setdefault("moodle", {})["url"] = url
    data["moodle"]["service"] = service
    _write_config_toml(data)


def _write_config_toml(data: dict) -> None:
    """將 dict 寫回 config.toml（保留結構）。"""
    from e3cli.config import CONFIG_FILE
    lines = []
    for section, values in data.items():
        if isinstance(values, dict):
            lines.append(f"[{section}]")
            for k, v in values.items():
                if isinstance(v, bool):
                    lines.append(f'{k} = {"true" if v else "false"}')
                elif isinstance(v, int):
                    lines.append(f"{k} = {v}")
                else:
                    lines.append(f'{k} = "{v}"')
            lines.append("")
    CONFIG_FILE.write_text("\n".join(lines) + "\n")


def clear_credentials(profile: str | None = None) -> None:
    """安全清除指定 profile 的認證資料。"""
    if profile is None:
        profile = get_active_profile()
    pdir = _profile_dir(profile)
    for path in [pdir / "credentials.enc", pdir / "key", pdir / "token"]:
        if path.exists():
            path.write_bytes(b"\x00" * max(path.stat().st_size, 1))
            path.unlink()
    # 刪除 profile metadata
    meta_file = pdir / "profile.json"
    if meta_file.exists():
        meta_file.unlink()
    # 如果刪的是 active profile，清主 token
    if profile == get_active_profile():
        if TOKEN_FILE.exists():
            TOKEN_FILE.write_bytes(b"\x00" * max(TOKEN_FILE.stat().st_size, 1))
            TOKEN_FILE.unlink()
    # 清除空目錄
    if pdir.exists() and not any(pdir.iterdir()):
        pdir.rmdir()


def has_credentials(profile: str | None = None) -> bool:
    if profile is None:
        profile = get_active_profile()
    pdir = _profile_dir(profile)
    return (pdir / "credentials.enc").exists() and (pdir / "key").exists()


# ─── Legacy migration ───────────────────────────────────────────────────

def _migrate_legacy() -> None:
    """將舊版單一帳號遷移到 default profile。"""
    if _LEGACY_CRED.exists() and _LEGACY_KEY.exists():
        dest = _profile_dir("default")
        if not (dest / "credentials.enc").exists():
            import shutil
            shutil.copy2(_LEGACY_CRED, dest / "credentials.enc")
            shutil.copy2(_LEGACY_KEY, dest / "key")
            # 複製 token
            if TOKEN_FILE.exists():
                shutil.copy2(TOKEN_FILE, dest / "token")
            # 從現有 config 讀取 moodle_url 作為 default profile 的設定
            try:
                from e3cli.config import load_config
                cfg = load_config()
                save_profile_meta("default", moodle_url=cfg.moodle.url, service=cfg.moodle.service)
            except Exception:
                pass
            set_active_profile("default")
        # 清除舊檔
        _LEGACY_CRED.unlink()
        _LEGACY_KEY.unlink()
