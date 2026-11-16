from cite_and_seek.eval.calibrate import confusion, sample_order


def test_sample_order_is_fixed_and_independent_of_input_order():
    ids = [f"Q{n:03d}" for n in range(1, 30)]
    first = sample_order(ids)
    assert first == sample_order(list(reversed(ids)))
    assert sorted(first) == sorted(ids)
    assert first != sorted(ids)


def test_confusion_compares_only_ids_both_labeled():
    judge = {"Q1": "correct", "Q2": "partial", "Q3": "judge_error", "Q4": "incorrect"}
    owner = {"Q1": "correct", "Q2": "incorrect", "Q3": "correct", "Q5": "skipped"}
    result = confusion(judge, owner)
    assert result["n"] == 2
    assert result["agree"] == 1
    assert result["matrix"]["partial"]["incorrect"] == 1
    assert result["matrix"]["correct"]["correct"] == 1
    assert result["disagreement_ids"] == ["Q2"]
