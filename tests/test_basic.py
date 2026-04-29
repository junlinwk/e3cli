"""基本測試 — 確認套件能正常載入。"""

import os

from e3cli import __version__
from e3cli.config import Config
from e3cli.course_name import (
    course_dir_name,
    display_name,
    display_with_code,
    migrate_course_dir,
    parse_course_name,
)
from e3cli.credential import _decrypt, _encrypt


def test_version():
    assert __version__


def test_default_config():
    cfg = Config()
    assert cfg.moodle.url == "https://e3p.nycu.edu.tw"
    assert cfg.moodle.service == "moodle_mobile_app"
    assert cfg.schedule.interval_minutes == 60


def test_encrypt_decrypt_roundtrip():
    key = os.urandom(32)
    plaintext = b"hello e3cli"
    encrypted = _encrypt(plaintext, key)
    decrypted = _decrypt(encrypted, key)
    assert decrypted == plaintext


def test_decrypt_wrong_key():
    key1 = os.urandom(32)
    key2 = os.urandom(32)
    encrypted = _encrypt(b"secret", key1)
    assert _decrypt(encrypted, key2) is None


def test_parse_course_name_bilingual():
    fullname = "1142.430107.Go人工智慧大數據平行運算 Artificial intelligent big data parallel computation by Go"
    code, zh, en = parse_course_name(fullname, "1142.430107")
    assert code == "1142.430107"
    assert zh == "Go人工智慧大數據平行運算"
    assert en == "Artificial intelligent big data parallel computation by Go"


def test_parse_course_name_chinese_only():
    code, zh, en = parse_course_name("1142.535510.作業系統設計", "1142.535510")
    assert code == "1142.535510"
    assert zh == "作業系統設計"
    assert en == ""


def test_parse_course_name_english_only():
    code, zh, en = parse_course_name("1142.999999.Operating Systems", "1142.999999")
    assert code == "1142.999999"
    assert zh == ""
    assert en == "Operating Systems"


def test_parse_course_name_legacy_underscore_format():
    code, zh, en = parse_course_name("1142_535510_2.作業系統 OS Design", "1142_535510_2")
    assert code == "1142_535510_2"
    assert zh == "作業系統"
    assert en == "OS Design"


def test_parse_course_name_no_shortname():
    code, zh, en = parse_course_name("1142.430107.測試 Test")
    assert code == "1142.430107"
    assert zh == "測試"
    assert en == "Test"


def test_parse_course_name_halfwidth_parens():
    code, zh, en = parse_course_name(
        "1142.410024.專題研究(三) Research(III)", "1142.410024"
    )
    assert code == "1142.410024"
    assert zh == "專題研究(三)"
    assert en == "Research(III)"


def test_parse_course_name_fullwidth_parens():
    code, zh, en = parse_course_name(
        "1142.410024.專題研究（三） Research(III)", "1142.410024"
    )
    assert code == "1142.410024"
    assert zh == "專題研究（三）"
    assert en == "Research(III)"


def test_parse_course_name_pure_chinese_with_parens():
    code, zh, en = parse_course_name("1142.410024.專題研究(三)", "1142.410024")
    assert code == "1142.410024"
    assert zh == "專題研究(三)"
    assert en == ""


def test_parse_course_name_chinese_with_period_then_english():
    # 中文後接句號或頓號再接英文（少見但要 robust）
    code, zh, en = parse_course_name(
        "1142.999999.資訊安全、密碼學 Information Security", "1142.999999"
    )
    assert zh == "資訊安全、密碼學"
    assert en == "Information Security"


def test_display_name_picks_language():
    fullname = "1142.430107.中文名稱 English Name"
    assert display_name(fullname, "1142.430107", lang="zh") == "中文名稱"
    assert display_name(fullname, "1142.430107", lang="en") == "English Name"


def test_display_name_fallback():
    # 純英文時，zh 模式 fallback 到英文
    assert display_name("1142.430107.Operating Systems", "1142.430107", lang="zh") == "Operating Systems"
    # 純中文時，en 模式 fallback 到中文
    assert display_name("1142.430107.作業系統", "1142.430107", lang="en") == "作業系統"


def test_display_with_code_format():
    fullname = "1142.430107.中文名 English"
    out = display_with_code(fullname, "1142.430107", lang="zh")
    assert out == "1142.430107  [bold]中文名[/bold]"
    out = display_with_code(fullname, "1142.430107", lang="en", bold_name=False)
    assert out == "1142.430107  English"


def test_course_dir_name_picks_language():
    fullname = "1142.430107.作業系統 Operating Systems"
    assert course_dir_name(fullname, "1142.430107", lang="zh") == "作業系統"
    assert course_dir_name(fullname, "1142.430107", lang="en") == "Operating Systems"


def test_course_dir_name_strips_unsafe():
    fullname = "1142.999999.中/文:名 Foo"
    # The slash and colon should be replaced by underscore
    assert course_dir_name(fullname, "1142.999999", lang="zh") == "中_文_名"


def test_migrate_course_dir_renames_legacy(tmp_path):
    legacy = tmp_path / "1142.430107"
    legacy.mkdir()
    (legacy / "file.txt").write_text("hi")

    fullname = "1142.430107.作業系統 Operating Systems"
    new_name = migrate_course_dir(tmp_path, fullname, "1142.430107", lang="zh")

    assert new_name == "作業系統"
    assert (tmp_path / "作業系統").exists()
    assert (tmp_path / "作業系統" / "file.txt").read_text() == "hi"
    assert not legacy.exists()


def test_migrate_course_dir_skips_when_new_already_exists(tmp_path):
    legacy = tmp_path / "1142.430107"
    legacy.mkdir()
    (legacy / "old.txt").write_text("old")
    new_dir = tmp_path / "作業系統"
    new_dir.mkdir()
    (new_dir / "new.txt").write_text("new")

    fullname = "1142.430107.作業系統 Operating Systems"
    migrate_course_dir(tmp_path, fullname, "1142.430107", lang="zh")

    # Both directories still exist; nothing was overwritten
    assert legacy.exists()
    assert (legacy / "old.txt").exists()
    assert (new_dir / "new.txt").exists()
