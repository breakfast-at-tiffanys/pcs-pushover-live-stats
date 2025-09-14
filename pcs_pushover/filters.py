"""Race filters and helpers for classification.

Provides utilities to:
- Normalize live/result URLs to a base race path.
- Classify a race via procyclingstats' Race scraper.
- Decide whether a race is Men's WorldTour or World Championships.
"""

from __future__ import annotations

import re

try:  # Optional import: only needed when classification is used
    from procyclingstats import Race as _PCS_Race  # type: ignore
except Exception:  # pragma: no cover - tested indirectly
    _PCS_Race = None  # type: ignore


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
    """Fetch race classification fields using PCS Race scraper.

    Args:
        base_path: Path like ``race/<name>/<year>``.

    Returns:
        Tuple of (uci_tour, category) or (None, None) if unavailable.
    """
    if _PCS_Race is None:
        return None, None
    try:
        race = _PCS_Race(base_path)  # type: ignore[call-arg]
        # These accessors may raise; guard individually
        try:
            tour = race.uci_tour()
        except Exception:
            tour = None
        try:
            cat = race.category()
        except Exception:
            cat = None
        return tour, cat
    except Exception:
        return None, None


def is_men_uwt_or_wc(uci_tour: str | None, category: str | None) -> bool:
    """Return True if the race is Men's WorldTour or World Championships.

    Args:
        uci_tour: e.g. "UCI Worldtour", "UCI ProSeries", "World Championships".
        category: e.g. "Men Elite", "ME - Men Elite", "Women Elite".
    """
    ut = (uci_tour or "").lower()
    cat = (category or "").lower()

    is_men = ("men" in cat) and ("women" not in cat)
    is_uwt = "worldtour" in ut
    is_wc = "world" in ut and "champ" in ut
    return is_men and (is_uwt or is_wc)
