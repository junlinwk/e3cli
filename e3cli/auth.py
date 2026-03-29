"""認證模組 — 透過 login/token.php 取得 Moodle Web Service token。"""

from __future__ import annotations

from e3cli.http import get_session_for_url


class AuthError(Exception):
    """認證失敗。"""


def get_token(base_url: str, username: str, password: str, service: str = "moodle_mobile_app") -> str:
    """
    向 Moodle 取得 Web Service token。

    POST {base_url}/login/token.php
    成功回傳 token 字串，失敗拋出 AuthError。
    """
    base_url = base_url.rstrip("/")
    url = f"{base_url}/login/token.php"
    session = get_session_for_url(base_url)
    resp = session.post(url, data={
        "username": username,
        "password": password,
        "service": service,
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "token" in data:
        return data["token"]

    error_msg = data.get("error", "未知錯誤")
    error_code = data.get("errorcode", "")

    # 登入失敗時檢查是否為 SSO-only 站點，提供更明確的提示
    if error_code == "invalidlogin":
        from e3cli.http import check_sso_only
        if check_sso_only(base_url):
            from e3cli.i18n import t
            raise AuthError(t("profile.url_sso_only"))

    raise AuthError(f"登入失敗 [{error_code}]: {error_msg}")
