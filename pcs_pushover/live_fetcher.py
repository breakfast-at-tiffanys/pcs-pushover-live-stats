"""Fetch and parse LiveStats JSON from PCS live pages."""

from __future__ import annotations

import json
import re
from types import SimpleNamespace
from typing import Any

from bs4 import BeautifulSoup

from .pcs_http import fetch_pcs_html, normalize_pcs_url


class LiveStatsClient:
    """Client to fetch and parse PCS LiveStats pages.

    Attributes:
        scraper: Namespace exposing the current page URL.
        last_html: The last fetched page HTML, if available.
    """

    def __init__(self, race_url: str) -> None:
        """Initialize the client.

        Args:
            race_url: Relative path (``race/.../live``) or absolute PCS URL.
        """
        self.scraper: Any = SimpleNamespace(url=normalize_pcs_url(race_url))
        self.last_html: str | None = None

    def refresh(self) -> dict[str, Any]:
        """Fetch latest HTML and extract the LiveStats JSON.

        Returns:
            dict[str, Any]: Parsed JSON object from the embedded ``var data``.
        """
        html, final_url = fetch_pcs_html(self.scraper.url)
        self.scraper.url = final_url
        self.last_html = html
        data = self._extract_data_json(html)
        return data

    def title(self) -> str:
        """Return a readable page title if available.

        Returns:
            str: The page title or ``"PCS LiveStats"`` as fallback.
        """
        try:
            if not self.last_html:
                return "PCS LiveStats"
            soup = BeautifulSoup(self.last_html, "html.parser")
            for selector in (
                ".page-title > .main > h1",
                ".page-title > .title > h1",
                ".page-title h1",
            ):
                title_node = soup.select_one(selector)
                if title_node is not None:
                    text = title_node.get_text(" ", strip=True)
                    if text:
                        return text
            title_tag = soup.find("title")
            if title_tag is not None:
                title = title_tag.get_text(" ", strip=True)
                title = re.sub(
                    r"\s+\|\s+ProCyclingStats(?:\.com)?$",
                    "",
                    title,
                )
                if title:
                    return title
        except Exception:
            return "PCS LiveStats"
        return "PCS LiveStats"

    @staticmethod
    def _extract_data_json(html: str) -> dict[str, Any]:
        """Extract the embedded ``var data`` JSON from page HTML.

        Args:
            html: Fetched HTML string of the live page.

        Returns:
            dict[str, Any]: Parsed JSON object.

        Raises:
            LiveStatsBlockedError: When PCS serves a bot-protection challenge.
            LiveStatsUnavailableError: When PCS signals a temporary outage.
            LiveStatsDataMissingError: When the ``var data`` block is missing
                from the page (race not live yet, wrong URL, or layout change).
        """
        m = re.search(r"var\s+data\s*=\s*(\{.*?\});", html, re.S)
        if not m:
            lower = html.lower()
            if "just a moment" in lower and "cloudflare" in lower:
                raise LiveStatsBlockedError(
                    "PCS blocked automated access with a Cloudflare challenge"
                )
            if "temporarily unavailable" in lower or "technical difficulties" in lower:
                raise LiveStatsUnavailableError(
                    "PCS page temporarily unavailable (technical difficulties)"
                )
            if "page not found" in lower or "404" in lower:
                raise LiveStatsDataMissingError("LiveStats page not found (check URL)")
            msg = (
                "LiveStats data not found in page. The race may not be live yet, "
                "or the page layout changed."
            )
            raise LiveStatsDataMissingError(msg)
        json_str = m.group(1)
        # JSON is valid as-is
        data = json.loads(json_str)
        return data

    @staticmethod
    def extract_id(html: str) -> str | None:
        """Extract the numeric page ``id`` from page HTML.

        Args:
            html: Fetched HTML string of the live page.

        Returns:
            str | None: The extracted id or ``None`` if not present.
        """
        m = re.search(r"var\s+id\s*=\s*(\d+);", html)
        return m.group(1) if m else None


class LiveStatsError(ValueError):
    """Base class for LiveStats extraction errors."""


class LiveStatsUnavailableError(LiveStatsError):
    """Raised when PCS indicates a temporary unavailability."""


class LiveStatsBlockedError(LiveStatsUnavailableError):
    """Raised when PCS serves a bot-protection challenge page."""


class LiveStatsDataMissingError(LiveStatsError):
    """Raised when no LiveStats ``var data`` block is found in the page."""
