"""
安全帳密儲存 — 使用 Fernet 對稱加密。

加密流程：
1. 首次使用時產生一組隨機 encryption key，存入 ~/.e3cli/key (chmod 600)
2. 帳號密碼以 JSON 加密後存入 ~/.e3cli/credentials.enc (chmod 600)
3. Key 與 credentials 分離，即使 credentials 外洩也無法解密

安全考量：
- key 檔案權限 0600，僅擁有者可讀
- 密碼從不以明文形式寫入磁碟
- 支援 logout 時安全清除所有認證資料
"""

from __future__ import annotations

import json

from cryptography.fernet import Fernet, InvalidToken

from e3cli.config import CONFIG_DIR, ensure_dirs

KEY_FILE = CONFIG_DIR / "key"
CRED_FILE = CONFIG_DIR / "credentials.enc"


def _get_or_create_key() -> bytes:
    """取得加密金鑰，不存在則產生新的。"""
    ensure_dirs()
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)
    return key


def _get_fernet() -> Fernet:
    return Fernet(_get_or_create_key())


def save_credentials(username: str, password: str) -> None:
    """加密儲存帳號密碼。"""
    ensure_dirs()
    f = _get_fernet()
    data = json.dumps({"username": username, "password": password}).encode()
    encrypted = f.encrypt(data)
    CRED_FILE.write_bytes(encrypted)
    CRED_FILE.chmod(0o600)


def load_credentials() -> tuple[str, str] | None:
    """
    讀取已儲存的帳密。

    回傳 (username, password) 或 None（不存在/解密失敗）。
    """
    if not CRED_FILE.exists() or not KEY_FILE.exists():
        return None
    try:
        f = _get_fernet()
        decrypted = f.decrypt(CRED_FILE.read_bytes())
        data = json.loads(decrypted)
        return data["username"], data["password"]
    except (InvalidToken, KeyError, json.JSONDecodeError):
        return None


def clear_credentials() -> None:
    """安全清除所有認證資料（帳密 + token + key）。"""
    for path in [CRED_FILE, KEY_FILE, CONFIG_DIR / "token"]:
        if path.exists():
            # 先覆寫再刪除，降低資料殘留風險
            path.write_bytes(b"\x00" * max(path.stat().st_size, 1))
            path.unlink()


def has_credentials() -> bool:
    """是否已儲存帳密。"""
    return CRED_FILE.exists() and KEY_FILE.exists()
