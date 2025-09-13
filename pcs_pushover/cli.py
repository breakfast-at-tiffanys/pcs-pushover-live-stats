"""PCS → Pushover CLI for live race notifications.

Tracks PCS LiveStats pages (single or auto-discovered) and sends Pushover
notifications only for: race start, 100/50/10 km to go, and finish.
"""

import argparse
import json
import re
import sys
import time
from typing import Any

from dotenv import load_dotenv

from .discover import discover_live_race_paths
from .live_fetcher import LiveStatsClient
from .notifier import PushoverNotifier
from .state import StateStore

# Optional rich printing; fall back to built-in print for test/CI environments
try:
    from rich import print as _rich_print  # type: ignore
except (
    Exception
):  # pragma: no cover - exercised implicitly in environments without rich

    def _rich_print(*args, **kwargs):  # type: ignore
        __builtins__["print"](*args, **kwargs)


# alias used in this module
print = _rich_print  # type: ignore

STRICT_KM_MARKERS = [100.0, 50.0, 10.0]


def _result_url(u: str | None) -> str | None:
    """Convert a live page URL to its result page.

    Args:
        u: Live page URL (may be ``None``).

    Returns:
        str | None: The corresponding result URL (``/live`` stripped) or
        ``None`` if the input was ``None``.
    """
    try:
        return re.sub(r"/live/?$", "", u or "") if u is not None else None
    except Exception:
        return u


def format_extra_row(row: dict[str, Any]) -> str:
    """Format an ``extra_results`` entry into a compact string.

    Args:
        row: Row from the ``extra_results`` JSON array.

    Returns:
        str: One-line description such as ``"KOM #1 Rider (5 pts) +2s"``.
    """
    # Example keys include: extra_id, ertype, rnk, ridername, pnt, bonis
    etypes = {
        1: "Sprint",
        2: "KOM",
        3: "Bonus",
    }
    kind = etypes.get(row.get("ertype"), f"Type {row.get('ertype')}")
    rank = row.get("rnk")
    name = row.get("ridername")
    pnt = row.get("pnt")
    bon = row.get("bonis")
    parts = [f"{kind}"]
    if rank is not None:
        parts.append(f"#{rank}")
    if name:
        parts.append(str(name))
    if pnt:
        parts.append(f"({pnt} pts)")
    if bon:
        parts.append(f"+{bon}s")
    return " ".join(parts)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    p = argparse.ArgumentParser(
        description=("PCS LiveStats → Pushover notifier (start, 100/50/10 km, finish)")
    )
    p.add_argument(
        "--race",
        help="PCS LiveStats page (relative like race/.../live or absolute URL)",
    )
    p.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Polling interval in seconds (default: 30)",
    )
    p.add_argument(
        "--auto",
        action="store_true",
        help="Auto-discover and track live races from PCS homepage",
    )
    p.add_argument(
        "--discovery-interval",
        type=int,
        default=120,
        help="Discovery refresh interval in seconds (default: 120)",
    )
    p.add_argument(
        "--pushover-token", default=None, help="Override PUSHOVER_TOKEN env var"
    )
    p.add_argument(
        "--pushover-user", default=None, help="Override PUSHOVER_USER env var"
    )
    p.add_argument("--once", action="store_true", help="Run once and exit")
    p.add_argument(
        "--debug", action="store_true", help="Print parsed data keys to stdout"
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Optional list of arguments (defaults to ``sys.argv`` when None).

    Returns:
        int: Process exit code (``0`` on success).
    """
    load_dotenv()
    args = build_parser().parse_args(argv)

    if not args.auto and not args.race:
        print("[red]Error:[/red] either provide --race or use --auto")
        return 2

    # notifier (shared)
    client = None
    notifier = None
    try:
        notifier = PushoverNotifier(args.pushover_token, args.pushover_user)
    except Exception as e:
        print(
            "[yellow]Warning:[/yellow] Pushover not configured (",
            e,
            ") — running in dry mode.",
        )

    def push(
        msg: str,
        link: str = "live",
        title: str | None = None,
        url_override: str | None = None,
    ):
        print(f"[green]Notify:[/green] {msg}")
        if notifier:
            try:
                url = url_override
                if not url and client is not None:
                    url = client.scraper.url
                if link == "result":
                    url = _result_url(url)
                notifier.send(message=msg, title=title, url=url)
            except Exception as e:
                print(f"[red]Pushover error:[/red] {e}")

    def handle(data: dict[str, Any], state: StateStore, race_key: str, race_title: str):
        nonlocal client
        if args.debug:
            keys = sorted(list(data.keys()))
            print("[dim]Keys:[/dim]", ", ".join(keys))

        # Parse basics we care about
        status_raw = (data.get("race_status") or "").lower()
        finished = bool(data.get("finished") == 1 or status_raw == "finished")
        sec_since_start = int(data.get("sec_since_start") or 0)

        # Determine if race started (status or timer)
        started = status_raw in {"running", "live", "started"} or (
            sec_since_start > 0 and not finished
        )

        # kmtogo handling
        kmtogo_val: float | None = None
        try:
            kmtogo = data.get("kmtogo")
            if kmtogo is not None:
                kmtogo_val = float(kmtogo)
        except Exception:
            kmtogo_val = None

        cur = state.for_race(race_key)
        prev_kmtogo = cur.get("prev_kmtogo")

        # 1) Notify when race starts (only on transition, not on first observation)
        if (
            started
            and not cur.get("notified_start")
            and cur.get("last_status") not in {"running", "live", "started"}
            and cur.get("last_status") is not None
        ):
            link_url = client.scraper.url if client is not None else None
            push("Race started", title=race_title, url_override=link_url)
            cur["notified_start"] = True

        # Keep `last_status` for next transition detection
        cur["last_status"] = (data.get("race_status") or "").lower()

        # 2) Notify at specific km-to-go crossings: 100, 50, 10
        if kmtogo_val is not None and prev_kmtogo is not None:
            notified_markers = set(cur.get("notified_km_markers") or [])
            for marker in STRICT_KM_MARKERS:
                # crossing from > marker to <= marker
                if (
                    marker not in notified_markers
                    and prev_kmtogo > marker >= kmtogo_val
                ):
                    link_url = client.scraper.url if client is not None else None
                    push(
                        f"{int(marker)} km to go",
                        title=race_title,
                        url_override=link_url,
                    )
                    notified_markers.add(marker)
            cur["notified_km_markers"] = sorted(list(notified_markers))

        # Update prev_kmtogo
        cur["prev_kmtogo"] = kmtogo_val

        # 3) Notify when finished
        if finished and not cur.get("notified_finish"):
            link_url = client.scraper.url if client is not None else None
            push("Finished", link="result", title=race_title, url_override=link_url)
            cur["notified_finish"] = True

        # Persist state
        state.update_race(race_key, cur)

    # Single-race mode
    if not args.auto:
        client = LiveStatsClient(args.race)
        # Initial fetch (build race key)
        try:
            data = client.refresh()
        except Exception as e:
            print(f"[red]Failed to load LiveStats:[/red] {e}")
            return 2

        race_html = client.last_html or ""
        race_id = LiveStatsClient.extract_id(race_html) or args.race
        race_title = client.title()
        race_key = str(race_id)

        print(f"[bold]Tracking:[/bold] {race_title} ({race_key})")

        state = StateStore()

        # Handle the first response
        handle(data, state, race_key, race_title)
        if args.once:
            if args.debug:
                print(json.dumps(data, indent=2)[:2000])
            return 0

        # Poll loop
        interval = max(5, int(args.interval))
        try:
            while True:
                time.sleep(interval)
                try:
                    data = client.refresh()
                except Exception as e:
                    print(f"[yellow]Fetch error, will retry:[/yellow] {e}")
                    continue
                handle(data, state, race_key, race_title)
        except KeyboardInterrupt:
            print("\nBye")
            return 0

    # Auto mode: discover and track multiple races
    state = StateStore()
    trackers: dict[str, dict[str, Any]] = {}
    last_discovery = 0.0
    interval = max(5, int(args.interval))
    discovery_interval = max(30, int(args.discovery_interval))

    try:
        while True:
            now = time.time()
            if now - last_discovery >= discovery_interval:
                last_discovery = now
                paths = discover_live_race_paths()
                # Add new trackers
                for path in paths:
                    url = (
                        path
                        if path.startswith("http")
                        else ("https://www.procyclingstats.com/" + path)
                    )
                    # Build a client and seed state
                    tmp_client = LiveStatsClient(url)
                    try:
                        data = tmp_client.refresh()
                    except Exception:
                        continue
                    race_html = tmp_client.last_html or ""
                    race_id = LiveStatsClient.extract_id(race_html) or url
                    race_key = str(race_id)
                    if race_key not in trackers:
                        trackers[race_key] = {
                            "client": tmp_client,
                            "title": tmp_client.title(),
                        }
                        # Preload status to current to avoid backfilled "started"
                        cur0 = state.for_race(race_key)
                        cur0.setdefault(
                            "last_status", (data.get("race_status") or "").lower()
                        )
                        state.update_race(race_key, cur0)
                        title_str = trackers[race_key]["title"]
                        print(f"[bold]Tracking:[/bold] {title_str} ({race_key})")

            # Poll each tracker
            for race_key, rec in list(trackers.items()):
                client = rec["client"]  # rebind for handle()
                race_title = rec["title"]
                try:
                    data = client.refresh()
                except Exception as e:
                    print(f"[yellow]Fetch error for {race_key}:[/yellow] {e}")
                    continue
                handle(data, state, race_key, race_title)

            if args.once:
                return 0

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nBye")
        return 0


if __name__ == "__main__":
    sys.exit(main())
