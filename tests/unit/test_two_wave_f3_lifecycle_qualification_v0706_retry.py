from scripts.run_two_wave_f3_lifecycle_qualification_transplant_v0706_retry import ordered_ordinal_counts


def test_v0706_retry_orders_ordinal_mapping_values_not_keys():
    counts = {"4": 10, "2": 11, "0": 11, "3": 11, "1": 11}
    assert ordered_ordinal_counts(counts) == [11, 11, 11, 11, 10]


def test_v0706_retry_accepts_already_ordered_sequence():
    assert ordered_ordinal_counts([11, 11, 11, 11, 10]) == [11, 11, 11, 11, 10]
