"""基本測試 — 確認套件能正常載入。"""

from e3cli import __version__
from e3cli.config import Config
from e3cli.credential import _decrypt, _encrypt, _get_or_create_key


def test_version():
    assert __version__ == "0.1.0"


def test_default_config():
    cfg = Config()
    assert cfg.moodle.url == "https://e3p.nycu.edu.tw"
    assert cfg.moodle.service == "moodle_mobile_app"
    assert cfg.schedule.interval_minutes == 60


def test_encrypt_decrypt_roundtrip():
    key = _get_or_create_key()
    plaintext = b"hello e3cli"
    encrypted = _encrypt(plaintext, key)
    decrypted = _decrypt(encrypted, key)
    assert decrypted == plaintext


def test_decrypt_wrong_key():
    import os
    key1 = os.urandom(32)
    key2 = os.urandom(32)
    encrypted = _encrypt(b"secret", key1)
    assert _decrypt(encrypted, key2) is None
