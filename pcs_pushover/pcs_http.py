"""HTTP helpers for fetching PCS pages.

These helpers centralize URL normalization and browser-like fetching for
ProCyclingStats pages. PCS live pages are currently protected by Cloudflare,
so a vanilla ``requests`` client can receive a challenge page instead of the
expected HTML.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any
from urllib.parse import urljoin

import requests


def _load_curl_requests() -> Any | None:
    """Load the optional ``curl_cffi.requests`` module.

    Returns:
        Any | None: Imported module or ``None`` when unavailable.
    """
    try:
        return import_module("curl_cffi.requests")
    except Exception:  # pragma: no cover - exercised when optional dep missing
        return None


curl_requests: Any | None = _load_curl_requests()

PCS_BASE_URL = "https://www.procyclingstats.com/"
PCS_HTTP_TIMEOUT = 20

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": PCS_BASE_URL,
}


def normalize_pcs_url(url_or_path: str) -> str:
    """Normalize a PCS path or URL to an absolute PCS URL.

    Args:
        url_or_path: Relative PCS path or absolute URL.

    Returns:
        str: Absolute PCS URL.
    """
    if url_or_path.startswith(("http://", "https://")):
        return url_or_path
    return urljoin(PCS_BASE_URL, url_or_path.lstrip("/"))


def fetch_pcs_html(
    url_or_path: str, timeout: int = PCS_HTTP_TIMEOUT
) -> tuple[str, str]:
    """Fetch PCS HTML and return the body plus final URL.

    Args:
        url_or_path: Relative PCS path or absolute URL.
        timeout: Request timeout in seconds.

    Returns:
        tuple[str, str]: Response HTML and final URL after redirects.

    Raises:
        requests.HTTPError: If PCS returns a non-success status code.
        requests.RequestException: If the request fails.
    """
    url = normalize_pcs_url(url_or_path)
    if curl_requests is not None:
        response: Any = curl_requests.get(url, impersonate="chrome", timeout=timeout)
        response.raise_for_status()
        return response.text, str(response.url)

    response = requests.get(url, headers=_BROWSER_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text, str(response.url)
