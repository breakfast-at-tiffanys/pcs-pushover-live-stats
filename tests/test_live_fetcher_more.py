from pcs_pushover import live_fetcher as lf
from pcs_pushover.live_fetcher import LiveStatsBlockedError
from pcs_pushover.live_fetcher import LiveStatsClient as L
from pcs_pushover.live_fetcher import (
    LiveStatsDataMissingError,
    LiveStatsUnavailableError,
)


def test_live_fetcher_refresh_parses_json(monkeypatch):
    def fake_fetch(url: str, timeout: int = 20):  # noqa: ARG001
        return (
            '<script>var id = 111; var data = {"race_status": "prerace", '
            '"kmtogo": 77.7};</script>',
            "https://www.procyclingstats.com/race/foo/2025/stage-1/live",
        )

    monkeypatch.setattr(lf, "fetch_pcs_html", fake_fetch)
    client = lf.LiveStatsClient("race/foo/2025/stage-1/live")
    data = client.refresh()
    assert data["race_status"] == "prerace"
    assert data["kmtogo"] == 77.7
    assert client.scraper.url.endswith("/race/foo/2025/stage-1/live")


def test_live_fetcher_title_fallback_to_title_tag():
    client = lf.LiveStatsClient("race/foo/2025/stage-1/live")
    client.last_html = (
        "<html><head><title>Stage 1 Live | ProCyclingStats</title></head></html>"
    )
    assert client.title() == "Stage 1 Live"


def test_live_fetcher_title_from_page_heading():
    client = lf.LiveStatsClient("race/foo/2025/stage-1/live")
    client.last_html = (
        '<div class="page-title"><div class="main"><h1>Exact Stage Title</h1>'
        "</div></div>"
    )
    assert client.title() == "Exact Stage Title"


def test_live_fetcher_title_fallback_without_html():
    client = lf.LiveStatsClient("race/foo/2025/stage-1/live")
    assert client.title() == "PCS LiveStats"


def test_live_fetcher_title_fallback_on_parser_error(monkeypatch):
    client = lf.LiveStatsClient("race/foo/2025/stage-1/live")
    client.last_html = "<html></html>"

    def boom(*args, **kwargs):  # noqa: ARG001
        raise RuntimeError("bad parser")

    monkeypatch.setattr(lf, "BeautifulSoup", boom)
    assert client.title() == "PCS LiveStats"


def test_live_fetcher_init_does_not_require_pcs_package():
    client = lf.LiveStatsClient("race/foo/2025/stage-1/live")
    assert client.scraper.url.endswith("/race/foo/2025/stage-1/live")


def test_extract_data_classifies_unavailable_missing_and_blocked():
    html1 = (
        "<div>Due to technical difficulties this page is temporarily unavailable.</div>"
    )
    try:
        L._extract_data_json(html1)
        raise AssertionError("expected LiveStatsUnavailableError")
    except LiveStatsUnavailableError:
        pass

    html2 = "<h1>Page not found</h1>"
    try:
        L._extract_data_json(html2)
        raise AssertionError("expected LiveStatsDataMissingError")
    except LiveStatsDataMissingError:
        pass

    html3 = "<title>Just a moment...</title><body>Cloudflare</body>"
    try:
        L._extract_data_json(html3)
        raise AssertionError("expected LiveStatsBlockedError")
    except LiveStatsBlockedError:
        pass
