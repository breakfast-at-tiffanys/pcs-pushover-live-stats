import pcs_pushover.filters as flt


class FakeRace:
    def __init__(self, base: str):
        self._base = base

    def uci_tour(self) -> str:
        if "boom_tour" in self._base:
            raise RuntimeError("fail tour")
        if "ok" in self._base or "boom_cat" in self._base:
            return "UCI Worldtour"
        return "UCI ProSeries"

    def category(self) -> str:
        if "boom_cat" in self._base:
            raise RuntimeError("fail category")
        return "Men Elite"


def test_classify_race(monkeypatch):
    monkeypatch.setattr(flt, "_PCS_Race", FakeRace)
    tour, cat = flt.classify_race("race/ok/2025")
    assert tour == "UCI Worldtour"
    assert cat == "Men Elite"

    # Tour accessor fails → returns (None, category)
    tour2, cat2 = flt.classify_race("race/boom_tour/2025")
    assert tour2 is None and cat2 == "Men Elite"

    # Category accessor fails → returns (tour, None)
    tour3, cat3 = flt.classify_race("race/boom_cat/2025")
    assert tour3 == "UCI Worldtour" and cat3 is None


def test_classify_race_none(monkeypatch):
    monkeypatch.setattr(flt, "_PCS_Race", None)
    tour, cat = flt.classify_race("race/anything/2025")
    assert tour is None and cat is None


def test_classify_race_exception(monkeypatch):
    class BoomRace:
        def __init__(self, base: str):  # noqa: ARG002
            raise RuntimeError("boom")

    monkeypatch.setattr(flt, "_PCS_Race", BoomRace)
    tour, cat = flt.classify_race("race/anything/2025")
    assert tour is None and cat is None
