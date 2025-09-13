"""Discover currently live PCS race tracker links.

This module scrapes the PCS homepage to find anchors that point to live
trackers (either stage live pages or one‑day race result/live pages),
normalizes them to relative paths, and de‑duplicates the results.
"""

import requests
from bs4 import BeautifulSoup


def discover_live_race_paths() -> list[str]:
    """Discover live PCS tracker links from the homepage.

    Returns:
        list[str]: Relative paths like ``race/.../live`` or
        ``race/.../result/live``. The list is de‑duplicated while preserving
        order.
    """
    url = "https://www.procyclingstats.com/"
    try:
        html = requests.get(url, timeout=15).text
    except Exception:
        return []
    soup = BeautifulSoup(html, "html.parser")
    paths: list[str] = []
    for a in soup.select('a[href*="/live"]'):
        href_val = a.get("href")
        if not isinstance(href_val, str) or not href_val:
            continue
        # Normalize to a relative path under race/
        # Strip domain if present, and any leading slash
        href = href_val.split("procyclingstats.com/")[-1].lstrip("/")
        if href.startswith("race/") and "/live" in href:
            paths.append(href)
    # Deduplicate while preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for p in paths:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq
