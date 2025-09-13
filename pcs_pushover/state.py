"""JSON-backed state storage for tracking per-race notifications.

Keeps deduplication info and progress (e.g., last status, km markers) so the
CLI avoids sending duplicate notifications across runs.
"""

import json
import os
from typing import Any


class StateStore:
    """Persist small dict-like state to a JSON file.

    Attributes:
        path: Path to the JSON file on disk.
    """

    def __init__(self, path: str = ".cache/state.json") -> None:
        """Create a new state store.

        Args:
            path: Filesystem path where the JSON data will be stored.
        """
        self.path = path
        self._state: dict[str, Any] = {}
        self._loaded = False

    def load(self) -> None:
        """Load state from disk if not already loaded."""
        if self._loaded:
            return
        try:
            if os.path.exists(self.path):
                with open(self.path, encoding="utf-8") as f:
                    self._state = json.load(f)
        except Exception:
            self._state = {}
        finally:
            self._loaded = True

    def save(self) -> None:
        """Atomically save state to disk."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, sort_keys=True)
        os.replace(tmp, self.path)

    def for_race(self, race_key: str) -> dict[str, Any]:
        """Get or initialize state bucket for a race.

        Args:
            race_key: Unique identifier for the race (e.g., page id).

        Returns:
            dict[str, Any]: Mutable mapping with the race state.
        """
        self.load()
        if race_key not in self._state:
            self._state[race_key] = {
                # legacy keys kept for forward compatibility
                "last_status": None,
                "last_km_bucket": None,
                "seen_extra_ids": [],
                # new strict notification tracking
                "notified_start": False,
                "notified_finish": False,
                "notified_km_markers": [],
                "prev_kmtogo": None,
            }
        return self._state[race_key]

    def update_race(self, race_key: str, patch: dict[str, Any]) -> None:
        """Apply a partial update to a race state and persist.

        Args:
            race_key: Race identifier key.
            patch: Mapping of keys to update in the race state.
        """
        self.load()
        cur = self._state.get(race_key, {})
        cur.update(patch)
        self._state[race_key] = cur
        self.save()
