"""基本測試 — 確認套件能正常載入。"""

from e3cli import __version__
from e3cli.config import Config, load_config
from e3cli.credential import _get_fernet


def test_version():
    assert __version__ == "0.1.0"


def test_default_config():
    cfg = Config()
    assert cfg.moodle.url == "https://e3p.nycu.edu.tw"
    assert cfg.moodle.service == "moodle_mobile_app"
    assert cfg.schedule.interval_minutes == 60


def test_fernet_roundtrip():
    f = _get_fernet()
    plaintext = b"hello e3cli"
    assert f.decrypt(f.encrypt(plaintext)) == plaintext
