"""Tests for the n2c2 harness: XML loader + F1 scoring (no data/key needed)."""

import os

from eligible.eval.n2c2 import load_record, score
from eligible.eval.n2c2.criteria import CRITERIA_CODES

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "n2c2_sample.xml")


def test_loader_parses_text_and_all_gold_labels():
    rec = load_record(FIXTURE)
    assert "type 2 diabetes" in rec.text
    assert set(rec.gold) == set(CRITERIA_CODES)  # all 13 present
    assert rec.gold["ABDOMINAL"] == "met"
    assert rec.gold["HBA1C"] == "met"
    assert rec.gold["DRUG-ABUSE"] == "not met"


def test_scoring_math():
    codes = ["A", "B"]
    golds = [{"A": "met", "B": "not met"}, {"A": "met", "B": "met"}]
    preds = [{"A": "met", "B": "met"}, {"A": "not met", "B": "met"}]
    rep = score(golds, preds, codes)

    a = next(s for s in rep.per_criterion if s.code == "A")
    assert (a.tp, a.fp, a.fn) == (1, 0, 1)
    assert abs(a.precision - 1.0) < 1e-9
    assert abs(a.recall - 0.5) < 1e-9
    assert abs(a.f1 - 2 / 3) < 1e-9

    # micro pools tp=2, fp=1, fn=1 -> F1 = 2/3; macro = mean(2/3, 2/3) = 2/3
    assert abs(rep.micro_f1 - 2 / 3) < 1e-9
    assert abs(rep.macro_f1 - 2 / 3) < 1e-9
    assert rep.n_records == 2


def test_perfect_predictions_score_one():
    # every criterion has a positive instance, so perfect preds -> F1 = 1
    codes = CRITERIA_CODES
    gold = {c: "met" for c in codes}
    rep = score([gold, gold], [gold, gold], codes)
    assert abs(rep.micro_f1 - 1.0) < 1e-9
    assert abs(rep.macro_f1 - 1.0) < 1e-9
