from types import SimpleNamespace

import pcs_pushover.live_fetcher as lf


class FakeScraper:
    def __init__(self, url: str):
        self._url = url
        self.html = None

    def update_html(self):
        # Minimal HTML embedding var data JSON
        self.html = SimpleNamespace(
            html=(
                '<script>var id = 111; var data = {"race_status": "prerace", "kmtogo": 77.7};</script>'
            )
        )


def test_live_fetcher_refresh_parses_json(monkeypatch):
    monkeypatch.setattr(lf, "_PCS_Scraper", FakeScraper)
    client = lf.LiveStatsClient("race/foo/2025/stage-1/live")
    data = client.refresh()
    assert data["race_status"] == "prerace"
    assert data["kmtogo"] == 77.7


def test_live_fetcher_title_fallback(monkeypatch):
    # Provide scraper that sets html to a simple object without css_first
    class ScraperNoTitle(FakeScraper):
        def __init__(self, url: str):
            super().__init__(url)
            # Set html to a minimal object that doesn't support css_first
            self.html = SimpleNamespace(
                html=("<html><head></head><body>No title</body></html>")
            )

    monkeypatch.setattr(lf, "_PCS_Scraper", ScraperNoTitle)
    client = lf.LiveStatsClient("race/foo/2025/stage-1/live")
    assert client.title() == "PCS LiveStats"


def test_live_fetcher_init_requires_pcs(monkeypatch):
    monkeypatch.setattr(lf, "_PCS_Scraper", None)
    try:
        lf.LiveStatsClient("race/foo/2025/stage-1/live")
        assert False, "expected ImportError when PCS scraper missing"
    except ImportError:
        pass
