"""
安全帳密儲存 — 純 Python stdlib 實作 (無需 cryptography/Rust)。

加密流程：
1. 首次使用時產生 32 bytes 隨機 key，存入 ~/.e3cli/key (chmod 600)
2. 帳密 JSON → PBKDF2 派生加密金鑰 → AES-like XOR stream cipher → base64 編碼
3. 加上 HMAC-SHA256 驗證完整性，防止竄改

安全模型：
- key 檔案權限 0600，僅擁有者可讀
- key 與 credentials 分離
- HMAC 驗證確保資料完整性
- 密碼從不以明文寫入磁碟
- logout 時覆寫後再刪除
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os

from e3cli.config import CONFIG_DIR, ensure_dirs

KEY_FILE = CONFIG_DIR / "key"
CRED_FILE = CONFIG_DIR / "credentials.enc"


def _get_or_create_key() -> bytes:
    """取得加密金鑰，不存在則產生新的。"""
    ensure_dirs()
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = os.urandom(32)
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)
    return key


def _derive_key(master_key: bytes, salt: bytes) -> bytes:
    """用 PBKDF2-HMAC-SHA256 派生加密金鑰。"""
    return hashlib.pbkdf2_hmac("sha256", master_key, salt, iterations=100_000)


def _xor_bytes(data: bytes, key_stream: bytes) -> bytes:
    """XOR data with repeating key stream."""
    return bytes(d ^ key_stream[i % len(key_stream)] for i, d in enumerate(data))


def _encrypt(plaintext: bytes, master_key: bytes) -> bytes:
    """加密：salt + HMAC + ciphertext，base64 編碼輸出。"""
    salt = os.urandom(16)
    derived = _derive_key(master_key, salt)
    ciphertext = _xor_bytes(plaintext, derived)
    mac = hmac.new(derived, ciphertext, hashlib.sha256).digest()
    # Format: salt (16) + mac (32) + ciphertext (variable)
    return base64.b64encode(salt + mac + ciphertext)


def _decrypt(encoded: bytes, master_key: bytes) -> bytes | None:
    """解密，驗證 HMAC 後回傳明文，失敗回傳 None。"""
    try:
        raw = base64.b64decode(encoded)
        if len(raw) < 48:  # salt(16) + mac(32) minimum
            return None
        salt = raw[:16]
        stored_mac = raw[16:48]
        ciphertext = raw[48:]
        derived = _derive_key(master_key, salt)
        # 驗證 HMAC
        expected_mac = hmac.new(derived, ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(stored_mac, expected_mac):
            return None
        return _xor_bytes(ciphertext, derived)
    except Exception:
        return None


def save_credentials(username: str, password: str) -> None:
    """加密儲存帳號密碼。"""
    ensure_dirs()
    key = _get_or_create_key()
    data = json.dumps({"username": username, "password": password}).encode()
    encrypted = _encrypt(data, key)
    CRED_FILE.write_bytes(encrypted)
    CRED_FILE.chmod(0o600)


def load_credentials() -> tuple[str, str] | None:
    """讀取已儲存的帳密，回傳 (username, password) 或 None。"""
    if not CRED_FILE.exists() or not KEY_FILE.exists():
        return None
    try:
        key = _get_or_create_key()
        decrypted = _decrypt(CRED_FILE.read_bytes(), key)
        if decrypted is None:
            return None
        data = json.loads(decrypted)
        return data["username"], data["password"]
    except (KeyError, json.JSONDecodeError):
        return None


def clear_credentials() -> None:
    """安全清除所有認證資料（帳密 + token + key）。"""
    for path in [CRED_FILE, KEY_FILE, CONFIG_DIR / "token"]:
        if path.exists():
            path.write_bytes(b"\x00" * max(path.stat().st_size, 1))
            path.unlink()


def has_credentials() -> bool:
    """是否已儲存帳密。"""
    return CRED_FILE.exists() and KEY_FILE.exists()
