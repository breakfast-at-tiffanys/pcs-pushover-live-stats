import json

import pcs_pushover.cli as cli
from pcs_pushover.live_fetcher import LiveStatsClient as RealLiveStatsClient


class FakeLiveStatsClient:
    default_seq = []

    # Provide the static helper used by CLI for IDs
    extract_id = staticmethod(RealLiveStatsClient.extract_id)

    def __init__(self, url: str):
        self._seq = list(type(self).default_seq) or [{}]
        self._last = self._seq[-1]
        self._url = url
        self.last_html = "<script>var id = 12345;</script>"

        class ScraperObj:
            def __init__(self, url):
                self.url = url

        self.scraper = ScraperObj(url)

    def refresh(self):
        self.last_html = "<script>var id = 12345;</script>"
        if self._seq:
            self._last = self._seq.pop(0)
        return self._last

    def title(self):
        return "Fake Race"


def test_cli_error_when_no_args(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    rc = cli.main([])
    assert rc == 2


def test_cli_single_race_two_cycles(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    # Two snapshots: prerace -> running crossing 100 and 50 km
    FakeLiveStatsClient.default_seq = [
        {
            "race_status": "prerace",
            "finished": 0,
            "kmtogo": 165.4,
            "sec_since_start": 0,
        },
        {
            "race_status": "running",
            "finished": 0,
            "kmtogo": 49.9,
            "sec_since_start": 10,
        },
    ]
    monkeypatch.setattr(cli, "LiveStatsClient", FakeLiveStatsClient)

    # Make the loop run one iteration after the initial handle, then exit
    calls = {"n": 0}

    def fake_sleep(_):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise KeyboardInterrupt()

    monkeypatch.setattr(cli.time, "sleep", fake_sleep)

    rc = cli.main(["--race", "race/example/2025/stage-1/live", "--interval", "1"])
    assert rc == 0

    # State persisted and updated
    state_path = tmp_path / ".cache" / "state.json"
    data = json.loads(state_path.read_text())
    # race key 12345 from last_html
    cur = data["12345"]
    assert cur["notified_start"] is True
    assert 100.0 in cur["notified_km_markers"]
    assert 50.0 in cur["notified_km_markers"]


def test_cli_single_race_once_finished(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    FakeLiveStatsClient.default_seq = [
        {
            "race_status": "finished",
            "finished": 1,
            "kmtogo": 0.0,
            "sec_since_start": 3600,
        },
    ]
    monkeypatch.setattr(cli, "LiveStatsClient", FakeLiveStatsClient)

    rc = cli.main(["--race", "race/example/2025/stage-1/live", "--once"])
    assert rc == 0

    # Verify finish persisted
    state_path = tmp_path / ".cache" / "state.json"
    data = json.loads(state_path.read_text())
    cur = data["12345"]
    assert cur["notified_finish"] is True


def test_cli_auto_once(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    # Discovery returns two races
    monkeypatch.setattr(
        cli,
        "discover_live_race_paths",
        lambda: [
            "race/foo/2025/stage-2/live",
            "race/bar/2025/result/live",
        ],
    )

    # Each client returns a finished snapshot (single pass in --once)
    FakeLiveStatsClient.default_seq = [
        {
            "race_status": "finished",
            "finished": 1,
            "kmtogo": 0.0,
            "sec_since_start": 3600,
        },
    ]
    monkeypatch.setattr(cli, "LiveStatsClient", FakeLiveStatsClient)

    rc = cli.main(["--auto", "--once"])
    assert rc == 0


def test_cli_single_race_once_debug_invalid_km(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    FakeLiveStatsClient.default_seq = [
        {
            "race_status": "prerace",
            "finished": 0,
            "kmtogo": "abc",
            "sec_since_start": 0,
        },
    ]
    monkeypatch.setattr(cli, "LiveStatsClient", FakeLiveStatsClient)
    rc = cli.main(["--race", "race/example/2025/stage-1/live", "--once", "--debug"])
    assert rc == 0


def test_cli_initial_refresh_failure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    class ErrClient(FakeLiveStatsClient):
        def refresh(self):
            raise RuntimeError("oops")

    monkeypatch.setattr(cli, "LiveStatsClient", ErrClient)
    rc = cli.main(["--race", "race/example/2025/stage-1/live"])
    assert rc == 2


def test_cli_loop_fetch_error_then_exit(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    class LoopErrClient(FakeLiveStatsClient):
        def __init__(self, url: str):
            super().__init__(url)
            # First call ok (for initial handle)
            type(self).default_seq = [
                {
                    "race_status": "prerace",
                    "finished": 0,
                    "kmtogo": 150.0,
                    "sec_since_start": 0,
                },
            ]
            self._err_after = False

        def refresh(self):
            if not self._err_after:
                self._err_after = True
                return super().refresh()
            raise RuntimeError("later failure")

    monkeypatch.setattr(cli, "LiveStatsClient", LoopErrClient)

    calls = {"n": 0}

    def fake_sleep(_):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise KeyboardInterrupt()

    monkeypatch.setattr(cli.time, "sleep", fake_sleep)
    rc = cli.main(["--race", "race/example/2025/stage-1/live", "--interval", "1"])
    assert rc == 0


def test_cli_auto_errors_and_keyboardinterrupt(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    # Two paths: one fails during discovery refresh(), one succeeds but fails on poll
    p1 = "race/fail-discovery/2025/stage-1/live"
    p2 = "race/fail-poll/2025/stage-2/live"
    monkeypatch.setattr(cli, "discover_live_race_paths", lambda: [p1, p2])

    class ClientByUrl(FakeLiveStatsClient):
        def __init__(self, url: str):
            super().__init__(url)
            self._url = url
            if p2 in url:
                type(self).default_seq = [
                    {
                        "race_status": "prerace",
                        "finished": 0,
                        "kmtogo": 120.0,
                        "sec_since_start": 0,
                    },
                ]

        def refresh(self):
            if p1 in self._url:
                raise RuntimeError("discovery fail")
            if p2 in self._url:
                # First call ok (discovery); then raise in poll
                if getattr(self, "_polled", False):
                    raise RuntimeError("poll fail")
                self._polled = True
            return super().refresh()

    monkeypatch.setattr(cli, "LiveStatsClient", ClientByUrl)

    def raise_kbd(_):
        raise KeyboardInterrupt()

    # Ensure loop ends via KeyboardInterrupt to cover auto interrupt branch
    monkeypatch.setattr(cli.time, "sleep", raise_kbd)
    rc = cli.main(["--auto", "--interval", "1"])
    assert rc == 0


def test_cli_push_uses_notifier_send(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    # Make it finish once to trigger a push
    FakeLiveStatsClient.default_seq = [
        {
            "race_status": "finished",
            "finished": 1,
            "kmtogo": 0.0,
            "sec_since_start": 3600,
        },
    ]
    monkeypatch.setattr(cli, "LiveStatsClient", FakeLiveStatsClient)

    calls = {"sent": 0}

    class FakeNotifier:
        def __init__(self, token=None, user=None):
            pass

        def send(self, message, title=None, url=None):
            calls["sent"] += 1

    monkeypatch.setattr(cli, "PushoverNotifier", FakeNotifier)
    rc = cli.main(["--race", "race/example/2025/stage-1/live", "--once"])
    assert rc == 0
    assert calls["sent"] == 1
