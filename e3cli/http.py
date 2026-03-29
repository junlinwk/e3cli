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


def check_sso_only(url: str) -> bool:
    """Check if a Moodle site only supports SSO login (no native auth).

    Looks at the login page for SSO redirect links and checks whether
    the native login form is functional.
    """
    import re

    url = url.rstrip("/")
    session = get_session_for_url(url)
    try:
        resp = session.get(f"{url}/login/index.php", timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return False
        text = resp.text

        # Indicators of SSO-only: login page has SSO links/buttons
        sso_patterns = [
            r'potentialidp',                # Moodle IDP list
            r'auth/shibboleth',             # Shibboleth
            r'auth/cas',                    # CAS
            r'auth/saml2',                  # SAML2
            r'SSO',                         # Generic SSO keyword in buttons/links
        ]
        has_sso = any(re.search(p, text, re.IGNORECASE) for p in sso_patterns)
        if not has_sso:
            return False

        # If SSO is present, test whether native login actually works
        # by sending a dummy login — if the server processes it via
        # token.php (returns invalidlogin), native auth is enabled
        # But we also need to check if the login form action points
        # to an external SSO URL (not Moodle itself)
        form_actions = re.findall(
            r'<form[^>]*id=["\']login["\'][^>]*action=["\']([^"\']+)["\']', text
        )
        if not form_actions:
            # Also check for form with loginbtn
            form_actions = re.findall(
                r'<form[^>]*action=["\']([^"\']+)["\'][^>]*>[\s\S]*?id=["\']loginbtn["\']', text
            )

        # Check if login form posts to the Moodle site itself
        parsed_url = urlparse(url)
        for action in form_actions:
            parsed_action = urlparse(action)
            action_host = parsed_action.hostname or parsed_url.hostname
            if action_host and action_host != parsed_url.hostname:
                # Form posts to external SSO — SSO only
                return True

        # Final check: see if SSO link contains a redirect/login URL
        # pointing to an external identity provider
        sso_links = re.findall(r'href=["\']([^"\']*(?:SSO|sso|cas|saml|shib)[^"\']*)["\']', text)
        for link in sso_links:
            link_parsed = urlparse(link)
            link_host = link_parsed.hostname
            if link_host and link_host != parsed_url.hostname:
                return True

        return False
    except Exception:
        return False
