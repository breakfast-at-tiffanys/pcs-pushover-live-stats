"""Fetch and parse LiveStats JSON from PCS live pages.

This module exposes ``LiveStatsClient`` which wraps the
``procyclingstats.Scraper`` to retrieve a live page and extract the embedded
``var data = {...};`` blob used by the PCS LiveStats tracker.
"""

import json
import re
from typing import Any

try:
    from procyclingstats import Scraper as _PCS_Scraper  # type: ignore
except Exception:  # pragma: no cover - only hit in test environments missing dep
    _PCS_Scraper = None  # type: ignore


class LiveStatsClient:
    """Client to fetch and parse PCS LiveStats pages.

    Attributes:
        scraper: The underlying ``procyclingstats.Scraper`` instance.
        last_html: The last fetched page HTML, if available.
    """

    def __init__(self, race_url: str) -> None:
        """Initialize the client.

        Args:
            race_url: Relative path (``race/.../live``) or absolute PCS URL.

        Raises:
            ImportError: If the ``procyclingstats`` package is unavailable.
        """
        # Accept relative (race/...) or absolute URLs
        if _PCS_Scraper is None:
            raise ImportError(
                "procyclingstats package is required to fetch LiveStats. "
                "Install it via pip or run within the project venv."
            )
        # Attribute typed as Any to avoid leaking Unknown from external lib
        self.scraper: Any = _PCS_Scraper(race_url)  # type: ignore[call-arg]
        self.last_html: str | None = None

    def refresh(self) -> dict[str, Any]:
        """Fetch latest HTML and extract the LiveStats JSON.

        Returns:
            dict[str, Any]: Parsed JSON object from the embedded ``var data``.
        """
        # Use Scraper to fetch (uses requests under the hood)
        self.scraper.update_html()
        html = self.scraper.html.html
        self.last_html = html
        data = self._extract_data_json(html)
        return data

    def title(self) -> str:
        """Return a readable page title if available.

        Returns:
            str: The page title or ``"PCS LiveStats"`` as fallback.
        """
        try:
            title_node = (
                self.scraper.html.css_first(".page-title > .main > h1")
                or self.scraper.html.css_first(".page-title > .title > h1")
                or self.scraper.html.css_first(".page-title h1")
            )
            return title_node.text(strip=True)
        except Exception:
            return "PCS LiveStats"

    @staticmethod
    def _extract_data_json(html: str) -> dict[str, Any]:
        """Extract the embedded ``var data`` JSON from page HTML.

        Args:
            html: Fetched HTML string of the live page.

        Returns:
            dict[str, Any]: Parsed JSON object.

        Raises:
            LiveStatsUnavailableError: When PCS signals a temporary outage.
            LiveStatsDataMissingError: When the ``var data`` block is missing
                from the page (race not live yet, wrong URL, or layout change).
        """
        m = re.search(r"var\s+data\s*=\s*(\{.*?\});", html, re.S)
        if not m:
            lower = html.lower()
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


class LiveStatsDataMissingError(LiveStatsError):
    """Raised when no LiveStats ``var data`` block is found in the page."""
