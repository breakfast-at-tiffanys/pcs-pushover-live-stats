from pcs_pushover.cli import STRICT_KM_MARKERS, _result_url


def test_result_url_strips_live_suffix():
    assert (
        _result_url("https://www.procyclingstats.com/race/foo/2025/stage-1/live")
        == "https://www.procyclingstats.com/race/foo/2025/stage-1"
    )
    assert (
        _result_url("https://www.procyclingstats.com/race/foo/2025/result/live")
        == "https://www.procyclingstats.com/race/foo/2025/result"
    )
    # unchanged if no /live
    url = "https://www.procyclingstats.com/race/foo/2025/stage-1"
    assert _result_url(url) == url


def test_strict_km_markers_defined():
    assert STRICT_KM_MARKERS == [100.0, 50.0, 10.0]


def test_result_url_handles_nonstring():
    # Should not throw and return the original value
    assert _result_url(None) is None  # type: ignore[arg-type]
