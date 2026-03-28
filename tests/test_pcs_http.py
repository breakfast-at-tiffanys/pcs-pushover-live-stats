from pcs_pushover import pcs_http


class FakeResponse:
    def __init__(self, text: str, url: str):
        self.text = text
        self.url = url
        self.checked = False

    def raise_for_status(self):
        self.checked = True


def test_normalize_pcs_url():
    assert (
        pcs_http.normalize_pcs_url("race/foo/2025/stage-1/live")
        == "https://www.procyclingstats.com/race/foo/2025/stage-1/live"
    )
    assert (
        pcs_http.normalize_pcs_url("https://www.procyclingstats.com/race/foo/2025")
        == "https://www.procyclingstats.com/race/foo/2025"
    )


def test_fetch_pcs_html_uses_curl_cffi(monkeypatch):
    calls = {}

    class FakeCurlRequests:
        @staticmethod
        def get(url: str, impersonate: str, timeout: int):
            calls["url"] = url
            calls["impersonate"] = impersonate
            calls["timeout"] = timeout
            return FakeResponse(
                "<html>ok</html>",
                "https://www.procyclingstats.com/race/foo/2025",
            )

    monkeypatch.setattr(pcs_http, "curl_requests", FakeCurlRequests)
    html, final_url = pcs_http.fetch_pcs_html("race/foo/2025")
    assert html == "<html>ok</html>"
    assert final_url == "https://www.procyclingstats.com/race/foo/2025"
    assert calls == {
        "url": "https://www.procyclingstats.com/race/foo/2025",
        "impersonate": "chrome",
        "timeout": pcs_http.PCS_HTTP_TIMEOUT,
    }


def test_fetch_pcs_html_falls_back_to_requests(monkeypatch):
    calls = {}

    def fake_get(url: str, headers: dict[str, str], timeout: int):
        calls["url"] = url
        calls["headers"] = headers
        calls["timeout"] = timeout
        return FakeResponse("<html>fallback</html>", url)

    monkeypatch.setattr(pcs_http, "curl_requests", None)
    monkeypatch.setattr(pcs_http.requests, "get", fake_get)
    html, final_url = pcs_http.fetch_pcs_html("race/foo/2025")
    assert html == "<html>fallback</html>"
    assert final_url == "https://www.procyclingstats.com/race/foo/2025"
    assert calls["url"] == "https://www.procyclingstats.com/race/foo/2025"
    assert calls["timeout"] == pcs_http.PCS_HTTP_TIMEOUT
    assert calls["headers"]["Referer"] == pcs_http.PCS_BASE_URL
