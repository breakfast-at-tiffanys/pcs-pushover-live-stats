from pcs_pushover.state import StateStore


def test_state_store_persistence(tmp_path):
    path = tmp_path / "state.json"
    store = StateStore(str(path))

    rkey = "race-1"
    state = store.for_race(rkey)
    # defaults
    assert state["last_status"] is None
    assert state["prev_kmtogo"] is None
    assert state["notified_km_markers"] == []

    # update and persist
    store.update_race(rkey, {"last_status": "prerace", "prev_kmtogo": 120.0})

    # reload new instance
    store2 = StateStore(str(path))
    s2 = store2.for_race(rkey)
    assert s2["last_status"] == "prerace"
    assert s2["prev_kmtogo"] == 120.0
