from pcs_pushover.discover import discover_live_race_paths


def test_discover_live_race_paths(monkeypatch):
    sample_html = """
    <html><body>
      <a href="/race/vuelta-a-espana/2025/stage-20/live">Live</a>
      <a href="race/gp-quebec/2025/result/live">Live</a>
      <a href="race/gp-quebec/2025/result/live">Live duplicate</a>
      <a href="">empty</a>
      <a href="/rider/tadej-pogacar">rider</a>
    </body></html>
    """

    class R:
        def __init__(self, text):
            self.text = text

    def fake_get(url, timeout=15):
        return R(sample_html)

    monkeypatch.setattr("pcs_pushover.discover.requests.get", fake_get)

    paths = discover_live_race_paths()
    assert "race/vuelta-a-espana/2025/stage-20/live" in paths
    assert "race/gp-quebec/2025/result/live" in paths
    # no duplicates
    assert paths.count("race/gp-quebec/2025/result/live") == 1


def test_discover_handles_request_error(monkeypatch):
    def boom(url, timeout=15):
        raise RuntimeError("network down")

    monkeypatch.setattr("pcs_pushover.discover.requests.get", boom)
    paths = discover_live_race_paths()
    assert paths == []
