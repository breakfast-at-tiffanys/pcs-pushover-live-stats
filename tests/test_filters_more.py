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
    monkeypatch.setattr(
        flt,
        "fetch_pcs_html",
        lambda base: (
            (
                "<li><div class='title'>UCI Tour: </div>"
                "<div class='value'>UCI Worldtour</div></li>"
            ),
            f"https://www.procyclingstats.com/{base}",
        ),
    )
    tour2, cat2 = flt.classify_race("race/boom_tour/2025")
    assert tour2 == "UCI Worldtour" and cat2 == "Men Elite"

    # Category accessor fails → returns (tour, None)
    monkeypatch.setattr(
        flt,
        "fetch_pcs_html",
        lambda base: (
            (
                "<li><div class='title'>Category: </div>"
                "<div class='value'>Men Elite</div></li>"
            ),
            f"https://www.procyclingstats.com/{base}",
        ),
    )
    tour3, cat3 = flt.classify_race("race/boom_cat/2025")
    assert tour3 == "UCI Worldtour" and cat3 == "Men Elite"


def test_classify_race_none(monkeypatch):
    monkeypatch.setattr(flt, "_PCS_Race", None)
    monkeypatch.setattr(
        flt,
        "fetch_pcs_html",
        lambda base: (
            (
                "<li><div class='title'>Category: </div>"
                "<div class='value'>Men Elite</div></li>"
                "<li><div class='title'>Classification: </div>"
                "<div class='value'>1.UWT</div></li>"
            ),
            f"https://www.procyclingstats.com/{base}",
        ),
    )
    tour, cat = flt.classify_race("race/anything/2025")
    assert tour == "1.UWT" and cat == "Men Elite"


def test_classify_race_exception(monkeypatch):
    class BoomRace:
        def __init__(self, base: str):  # noqa: ARG002
            raise RuntimeError("boom")

    monkeypatch.setattr(flt, "_PCS_Race", BoomRace)
    monkeypatch.setattr(
        flt,
        "fetch_pcs_html",
        lambda base: (
            (
                "<li><div class='title'>Category: </div>"
                "<div class='value'>Woman Elite</div></li>"
                "<li><div class='title'>UCI Tour: </div>"
                "<div class='value'>UCI Women's WorldTour</div></li>"
            ),
            f"https://www.procyclingstats.com/{base}",
        ),
    )
    tour, cat = flt.classify_race("race/anything/2025")
    assert tour == "UCI Women's WorldTour" and cat == "Woman Elite"


def test_classify_race_returns_partial_when_fetch_fails(monkeypatch):
    class PartialRace:
        def __init__(self, base: str):
            self._base = base

        def uci_tour(self) -> str:
            return "UCI Worldtour"

        def category(self) -> str:
            raise RuntimeError("missing category")

    monkeypatch.setattr(flt, "_PCS_Race", PartialRace)
    monkeypatch.setattr(
        flt,
        "fetch_pcs_html",
        lambda base: (_ for _ in ()).throw(RuntimeError(base)),
    )
    tour, cat = flt.classify_race("race/anything/2025")
    assert tour == "UCI Worldtour" and cat is None


def test_extract_fact_value_skips_incomplete_items():
    html = (
        "<ul>"
        "<li><div class='title'>Category:</div></li>"
        "<li><div class='title'>Category:</div><div class='value'>Men Elite</div></li>"
        "</ul>"
    )
    tour, cat = flt._extract_race_metadata(html)
    assert tour is None
    assert cat == "Men Elite"
