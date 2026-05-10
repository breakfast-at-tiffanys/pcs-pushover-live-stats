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

    monkeypatch.setattr(
        "pcs_pushover.discover.fetch_pcs_html",
        lambda url, **kwargs: (sample_html, url),
    )

    paths = discover_live_race_paths()
    assert "race/vuelta-a-espana/2025/stage-20/live" in paths
    assert "race/gp-quebec/2025/result/live" in paths
    # no duplicates
    assert paths.count("race/gp-quebec/2025/result/live") == 1


def test_discover_handles_request_error(monkeypatch):
    def boom(url, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("pcs_pushover.discover.fetch_pcs_html", boom)
    paths = discover_live_race_paths()
    assert paths == []
