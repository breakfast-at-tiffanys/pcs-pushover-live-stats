import pcs_pushover.notifier as nt


def test_notifier_init_missing_env_raises(monkeypatch):
    monkeypatch.delenv("PUSHOVER_TOKEN", raising=False)
    monkeypatch.delenv("PUSHOVER_USER", raising=False)
    try:
        nt.PushoverNotifier()
        assert False, "Expected ValueError for missing credentials"
    except ValueError:
        pass


def test_notifier_send(monkeypatch):
    calls = {}

    class R:
        def __init__(self):
            self.data = None

        def raise_for_status(self):
            calls["ok"] = True

    def fake_post(url, data=None, timeout=10):
        calls["url"] = url
        calls["data"] = data
        return R()

    monkeypatch.setattr(nt.requests, "post", fake_post)
    n = nt.PushoverNotifier(token="ttt", user="uuu")
    long_msg = "x" * 2000
    n.send(long_msg, title="Stage", url="https://example.com/live", priority=1)
    assert calls["ok"] is True
    assert calls["url"].endswith("/1/messages.json")
    assert calls["data"]["token"] == "ttt"
    assert calls["data"]["user"] == "uuu"
    assert len(calls["data"]["message"]) == 1024  # trimmed
    assert calls["data"]["priority"] == "1"
