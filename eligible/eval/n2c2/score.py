"""Scoring for n2c2 cohort selection.

Per-criterion precision/recall/F1 for the positive ("met") class, plus
micro-averaged F1 (pool all criteria) and macro-averaged F1 (mean of
per-criterion F1). Micro-F1 was the shared task's primary ranking metric.
"""

from __future__ import annotations

from dataclasses import dataclass

from eligible.eval.n2c2.criteria import MET


@dataclass
class CriterionScore:
    code: str
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


@dataclass
class Report:
    per_criterion: list[CriterionScore]
    micro_f1: float
    macro_f1: float
    n_records: int

    def to_table(self) -> str:
        rows = [f"{'criterion':<16} {'P':>6} {'R':>6} {'F1':>6}"]
        rows.append("-" * 36)
        for s in self.per_criterion:
            rows.append(f"{s.code:<16} {s.precision:>6.3f} {s.recall:>6.3f} {s.f1:>6.3f}")
        rows.append("-" * 36)
        rows.append(f"{'micro-F1':<16} {'':>6} {'':>6} {self.micro_f1:>6.3f}")
        rows.append(f"{'macro-F1':<16} {'':>6} {'':>6} {self.macro_f1:>6.3f}")
        rows.append(f"(over {self.n_records} records)")
        return "\n".join(rows)


def score(golds: list[dict[str, str]], preds: list[dict[str, str]], codes: list[str]) -> Report:
    """Score aligned lists of gold/pred label dicts. `met` is the positive class."""
    if len(golds) != len(preds):
        raise ValueError("golds and preds must align")

    per: list[CriterionScore] = []
    tot_tp = tot_fp = tot_fn = 0
    for code in codes:
        tp = fp = fn = 0
        for g, p in zip(golds, preds):
            gold_met = g.get(code) == MET
            pred_met = p.get(code) == MET
            if gold_met and pred_met:
                tp += 1
            elif pred_met and not gold_met:
                fp += 1
            elif gold_met and not pred_met:
                fn += 1
        per.append(CriterionScore(code, tp, fp, fn))
        tot_tp, tot_fp, tot_fn = tot_tp + tp, tot_fp + fp, tot_fn + fn

    micro_p = tot_tp / (tot_tp + tot_fp) if (tot_tp + tot_fp) else 0.0
    micro_r = tot_tp / (tot_tp + tot_fn) if (tot_tp + tot_fn) else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) else 0.0
    macro_f1 = sum(s.f1 for s in per) / len(per) if per else 0.0

    return Report(per_criterion=per, micro_f1=micro_f1, macro_f1=macro_f1, n_records=len(golds))
