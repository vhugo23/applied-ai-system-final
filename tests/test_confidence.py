import pytest

from src import recommender as r
from src.recommender import recommendation_confidence


def result(score, *reasons):
    return ({"title": "t"}, score, list(reasons))


def test_empty_results_zero():
    assert recommendation_confidence([]) == 0.0


def test_weights_sum_to_one():
    total = r.CONFIDENCE_GAP_WEIGHT + r.CONFIDENCE_SPREAD_WEIGHT + r.CONFIDENCE_LABEL_WEIGHT
    assert total == pytest.approx(1.0)


def test_maximum_confidence_is_one():
    results = [result(6.0, "genre match (+2.000)"), result(5.0), result(4.0), result(3.0), result(2.0)]
    assert recommendation_confidence(results) == pytest.approx(1.0)


def test_no_label_match_loses_label_share():
    results = [result(6.0), result(5.0), result(4.0), result(3.0), result(2.0)]
    assert recommendation_confidence(results) == pytest.approx(0.6)


def test_secondary_label_gets_half_label_share():
    results = [result(6.0, "secondary mood match (+0.500)"), result(5.0), result(4.0)]
    assert recommendation_confidence(results) == pytest.approx(0.6 + 0.4 * 0.5)


def test_tied_flat_results_with_no_label_are_zero():
    assert recommendation_confidence([result(3.0), result(3.0), result(3.0)]) == 0.0


def test_single_result_has_no_gap_or_spread():
    assert recommendation_confidence([result(5.0, "mood match (+1.000)")]) == pytest.approx(0.4)


def test_bigger_gap_means_higher_confidence():
    small = [result(5.0, "genre match"), result(4.9), result(4.0)]
    big = [result(5.0, "genre match"), result(4.0), result(4.0)]
    assert recommendation_confidence(big) > recommendation_confidence(small)


def test_confidence_is_an_alias_of_recommendation_confidence():
    results = [result(6.0, "genre match (+2.000)"), result(5.0), result(4.0)]
    assert r.confidence is recommendation_confidence
    assert r.confidence(results) == recommendation_confidence(results)
    assert 0.0 <= r.confidence(results) <= 1.0
