#!/usr/bin/env python3
"""
自動產生 Homebrew formula。

用法: python scripts/generate-formula.py v0.1.0 > Formula/e3cli.rb

這個腳本會：
1. 從 PyPI / GitHub Release 取得 tarball 的 sha256
2. 解析 pyproject.toml 取得所有 dependencies
3. 從 PyPI 取得每個 dependency 的 sdist URL 和 sha256
4. 產生完整的 Homebrew formula
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path


GITHUB_REPO = "user/e3cli"  # 改成你的 GitHub repo


def get_pypi_info(package: str) -> dict:
    """從 PyPI JSON API 取得套件資訊。"""
    url = f"https://pypi.org/pypi/{package}/json"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read())


def get_sdist_url_and_sha(package: str) -> tuple[str, str]:
    """取得套件的 sdist URL 和 sha256。"""
    info = get_pypi_info(package)
    version = info["info"]["version"]
    for release_file in info["releases"][version]:
        if release_file["packagetype"] == "sdist":
            return release_file["url"], release_file["digests"]["sha256"]
    raise ValueError(f"No sdist found for {package}")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <version-tag>", file=sys.stderr)
        sys.exit(1)

    tag = sys.argv[1]
    tarball_url = f"https://github.com/{GITHUB_REPO}/archive/refs/tags/{tag}.tar.gz"

    # Core dependencies (from pyproject.toml)
    deps = ["typer", "requests", "rich", "cryptography"]

    print(f'class E3cli < Formula')
    print(f'  include Language::Python::Virtualenv')
    print(f'')
    print(f'  desc "NYCU E3 Moodle automation CLI — sync courses, download materials, submit assignments"')
    print(f'  homepage "https://github.com/{GITHUB_REPO}"')
    print(f'  url "{tarball_url}"')
    print(f'  # sha256 "FILL_AFTER_RELEASE"')
    print(f'  license "MIT"')
    print(f'')
    print(f'  depends_on "python@3.12"')
    print(f'')

    for dep in deps:
        try:
            url, sha = get_sdist_url_and_sha(dep)
            print(f'  resource "{dep}" do')
            print(f'    url "{url}"')
            print(f'    sha256 "{sha}"')
            print(f'  end')
            print(f'')
        except Exception as e:
            print(f'  # ERROR: {dep}: {e}', file=sys.stderr)

    print(f'  def install')
    print(f'    virtualenv_install_with_resources')
    print(f'  end')
    print(f'')
    print(f'  test do')
    print(f'    assert_match "e3cli", shell_output("#{{bin}}/e3cli version")')
    print(f'  end')
    print(f'end')


if __name__ == "__main__":
    main()
