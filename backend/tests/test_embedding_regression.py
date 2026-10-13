from evaluation.embedding_regression import _pairs, _score


def test_pairwise_group_score_penalizes_split_expected_group() -> None:
    expected = [{"S1", "S2", "S3"}]
    actual = [{"S1", "S2"}]

    assert _pairs(expected) == {("S1", "S2"), ("S1", "S3"), ("S2", "S3")}
    assert _score(expected, actual) == {
        "pair_precision": 1.0,
        "pair_recall": 1 / 3,
        "pair_f1": 0.5,
    }


def test_pairwise_group_score_penalizes_unrelated_merge() -> None:
    score = _score([{"S1", "S2"}], [{"S1", "S2", "S3"}])

    assert score["pair_precision"] == 1 / 3
    assert score["pair_recall"] == 1.0
    assert score["pair_f1"] == 0.5
