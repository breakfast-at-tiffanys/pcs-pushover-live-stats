from pcs_pushover.cli import format_extra_row


def test_format_extra_row_variants():
    # KOM with rank and points and bonus seconds
    row = {"ertype": 2, "rnk": 1, "ridername": "Rider A", "pnt": 5, "bonis": 2}
    s = format_extra_row(row)
    assert s.startswith("KOM #1 Rider A (5 pts) +2s")

    # Sprint without bonus
    row2 = {"ertype": 1, "rnk": 3, "ridername": "Rider B", "pnt": 10}
    s2 = format_extra_row(row2)
    assert s2.startswith("Sprint #3 Rider B (10 pts)")

    # Unknown type
    row3 = {"ertype": 7, "rnk": 2, "ridername": "Rider C"}
    s3 = format_extra_row(row3)
    assert s3.startswith("Type 7 #2 Rider C")
