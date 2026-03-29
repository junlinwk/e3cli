"""HTTP session factory — handles legacy SSL servers gracefully."""

from __future__ import annotations

import ssl
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# Cache: host → needs legacy SSL (True/False)
_legacy_ssl_cache: dict[str, bool] = {}


class _LegacySSLAdapter(HTTPAdapter):
    """HTTPAdapter that allows unsafe legacy TLS renegotiation.

    Some older Moodle servers (e.g. NCCU) do not support RFC 5746 secure
    renegotiation.  Modern OpenSSL/LibreSSL refuses to connect by default.
    This adapter relaxes that restriction so the connection succeeds.
    """

    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        # Allow legacy renegotiation
        ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def create_session(legacy_ssl: bool = False) -> requests.Session:
    """Create a requests.Session, optionally with legacy SSL support."""
    session = requests.Session()
    if legacy_ssl:
        adapter = _LegacySSLAdapter()
        session.mount("https://", adapter)
    return session


def _needs_legacy_ssl(url: str) -> bool:
    """Test whether a URL requires legacy SSL by attempting a quick HEAD request.

    Results are cached per host to avoid repeated probes.
    """
    host = urlparse(url).hostname or url
    if host in _legacy_ssl_cache:
        return _legacy_ssl_cache[host]

    try:
        requests.head(url, timeout=5, allow_redirects=True)
        _legacy_ssl_cache[host] = False
        return False
    except requests.exceptions.SSLError as e:
        if "UNSAFE_LEGACY_RENEGOTIATION" in str(e):
            _legacy_ssl_cache[host] = True
            return True
        raise


def get_session_for_url(url: str) -> requests.Session:
    """Return a session appropriate for the given URL, auto-detecting legacy SSL."""
    try:
        return create_session(legacy_ssl=_needs_legacy_ssl(url))
    except Exception:
        # If detection itself fails for non-SSL reasons, return a normal session
        return create_session()


def validate_moodle_url(url: str) -> tuple[bool, str]:
    """Validate whether a URL points to a reachable Moodle instance.

    Returns (ok, message).  When ok is False, message describes the problem
    in a user-friendly way.
    """
    url = url.rstrip("/")

    # Basic format check
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.hostname:
        return False, "Invalid URL format"

    # Try to reach the login/token.php endpoint (Moodle-specific)
    session = get_session_for_url(url)
    try:
        resp = session.get(f"{url}/login/token.php", timeout=10, allow_redirects=True)
        # Moodle token endpoint returns JSON even without params
        # A non-Moodle site would return HTML 404 or something else
        if resp.status_code == 200:
            return True, "OK"
        return False, f"HTTP {resp.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Connection failed — check the URL"
    except requests.exceptions.Timeout:
        return False, "Connection timed out"
    except requests.exceptions.SSLError as e:
        return False, f"SSL error: {e}"
    except requests.exceptions.RequestException as e:
        return False, str(e)
