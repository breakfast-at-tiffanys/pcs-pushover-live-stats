import json

from pcs_pushover.live_fetcher import LiveStatsClient


def test_extract_data_json_basic():
    data_obj = {"race_status": "prerace", "kmtogo": 123.4}
    html = f"""
    <html><head></head><body>
    <script>
    var id = 282552;
    var data = {json.dumps(data_obj)};
    </script>
    </body></html>
    """
    parsed = LiveStatsClient._extract_data_json(html)
    assert parsed["race_status"] == "prerace"
    assert parsed["kmtogo"] == 123.4


def test_extract_id():
    html = "<script>var id = 987654;</script>"
    assert LiveStatsClient.extract_id(html) == "987654"
    assert LiveStatsClient.extract_id("<script></script>") is None


def test_extract_data_missing_raises():
    from pcs_pushover.live_fetcher import LiveStatsClient as L

    try:
        L._extract_data_json("<html>no data here</html>")
        assert False, "expected ValueError"
    except ValueError:
        pass
