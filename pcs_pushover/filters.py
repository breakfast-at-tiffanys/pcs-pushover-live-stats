"""Race filters and helpers for classification.

Provides utilities to:
- Normalize live/result URLs to a base race path.
- Classify a race via the PCS package or direct PCS HTML.
- Decide whether a race is Men's WorldTour or World Championships.
"""

from __future__ import annotations

import re
from typing import Protocol, cast

from bs4 import BeautifulSoup

from .pcs_http import fetch_pcs_html

try:  # Optional import: only needed when classification is used
    from procyclingstats import Race as _PCS_Race  # type: ignore
except Exception:  # pragma: no cover - tested indirectly
    _PCS_Race = None  # type: ignore


class _RaceLike(Protocol):
    """Protocol for the PCS race object methods used by this module."""

    def uci_tour(self) -> str | None:
        """Return the UCI tour label."""

    def category(self) -> str | None:
        """Return the race category label."""


def race_base_from_path(url_or_path: str) -> str | None:
    """Normalize any PCS race/live URL or path to a base ``race/<name>/<year>``.

    Examples:
        - ``https://www.procyclingstats.com/race/tour-de-france/2024/stage-1/live``
          → ``race/tour-de-france/2024``
        - ``race/paris-roubaix/2025/result/live`` → ``race/paris-roubaix/2025``
        - ``race/world-championship/2025`` → ``race/world-championship/2025``

    Args:
        url_or_path: Absolute URL or relative PCS path.

    Returns:
        The normalized base path or ``None`` if it doesn't look like a PCS race.
    """
    if not url_or_path:
        return None

    # Strip scheme/domain if present
    path = re.sub(r"^https?://[^/]+/", "", url_or_path).lstrip("/")
    if not path.startswith("race/"):
        return None

    # Remove common live suffixes
    path = re.sub(r"/(result/)?live/?$", "", path)
    # Remove stage segment, including any trailing parts
    path = re.sub(r"/stage-\d+(?:/.*)?$", "", path)

    # keep only race/<name>/<year>
    parts = path.split("/")
    if len(parts) >= 3:
        return "/".join(parts[:3])
    return path or None


def classify_race(base_path: str) -> tuple[str | None, str | None]:
    """Fetch race classification fields for a PCS race.

    Args:
        base_path: Path like ``race/<name>/<year>``.

    Returns:
        Tuple of (uci_tour, category) or (None, None) if unavailable.
    """
    tour: str | None = None
    cat: str | None = None

    if _PCS_Race is not None:
        race: _RaceLike | None = None
        try:
            race = cast(_RaceLike, _PCS_Race(base_path))  # type: ignore[call-arg]
        except Exception:
            race = None

        if race is not None:
            # These accessors may raise; guard individually
            try:
                tour = race.uci_tour()
            except Exception:
                tour = None
            try:
                cat = race.category()
            except Exception:
                cat = None

    if tour and cat:
        return tour, cat

    try:
        html, _ = fetch_pcs_html(base_path)
        meta_tour, meta_cat = _extract_race_metadata(html)
        return tour or meta_tour, cat or meta_cat
    except Exception:
        return tour, cat


def _extract_race_metadata(html: str) -> tuple[str | None, str | None]:
    """Extract race metadata from a PCS race page.

    Args:
        html: Race page HTML.

    Returns:
        tuple[str | None, str | None]: ``(uci_tour, category)`` fields.
    """
    soup = BeautifulSoup(html, "html.parser")
    category = _extract_fact_value(soup, "Category")
    uci_tour = _extract_fact_value(soup, "UCI Tour")
    if not uci_tour:
        uci_tour = _extract_fact_value(soup, "Classification")
    return uci_tour, category


def _extract_fact_value(soup: BeautifulSoup, label: str) -> str | None:
    """Extract a labeled fact value from a PCS race page.

    Args:
        soup: Parsed race page HTML.
        label: Label text such as ``"Category"`` or ``"UCI Tour"``.

    Returns:
        str | None: Matched value or ``None`` when not present.
    """
    want = label.lower().rstrip(":")
    for item in soup.select("li"):
        title_node = item.select_one(".title")
        value_node = item.select_one(".value")
        if title_node is None or value_node is None:
            continue
        got = title_node.get_text(" ", strip=True).lower().rstrip(":")
        if got != want:
            continue
        value = value_node.get_text(" ", strip=True)
        return value or None
    return None


def is_men_uwt_or_wc(uci_tour: str | None, category: str | None) -> bool:
    """Return True if the race is Men's WorldTour or World Championships.

    Args:
        uci_tour: e.g. "UCI Worldtour", "UCI ProSeries", "World Championships".
        category: e.g. "Men Elite", "ME - Men Elite", "Women Elite".
    """
    ut = (uci_tour or "").lower()
    norm_ut = ut.replace(" ", "")
    cat = (category or "").lower()

    is_men = ("men" in cat) and ("women" not in cat)
    # Accept both full label and acronym
    is_uwt = ("worldtour" in norm_ut) or ("uwt" in ut)
    # Accept common full labels and the "WC" acronym (word-boundary)
    is_wc = ("world" in ut and "champ" in ut) or (re.search(r"\bwc\b", ut) is not None)
    return is_men and (is_uwt or is_wc)
