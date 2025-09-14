from pcs_pushover.filters import is_men_uwt_or_wc, race_base_from_path


def test_race_base_from_path_cases():
    assert (
        race_base_from_path(
            "https://www.procyclingstats.com/race/tour-de-france/2024/stage-1/live"
        )
        == "race/tour-de-france/2024"
    )
    assert (
        race_base_from_path("race/paris-roubaix/2025/result/live")
        == "race/paris-roubaix/2025"
    )
    assert (
        race_base_from_path("race/world-championship/2025")
        == "race/world-championship/2025"
    )
    assert race_base_from_path("rider/jonas-vingegaard-rasmussen") is None
    assert race_base_from_path("") is None
    assert race_base_from_path("race/onepart") == "race/onepart"


def test_is_men_uwt_or_wc():
    assert is_men_uwt_or_wc("UCI Worldtour", "Men Elite")
    assert is_men_uwt_or_wc("World Championships", "ME - Men Elite")
    assert not is_men_uwt_or_wc("UCI ProSeries", "Men Elite")
    assert not is_men_uwt_or_wc("UCI Worldtour", "Women Elite")
