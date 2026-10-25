"""Run the n2c2 cohort-selection benchmark end to end.

Loads gold-labeled records, classifies each with the pro+thinking annotator,
scores per-criterion + micro/macro F1. Requires the n2c2 2018 Track 1 data
(gated by DUA) under --data, and DEEPSEEK_API_KEY.

Run:  python eval/n2c2/run.py --data data/n2c2/test [--limit N]
"""

from __future__ import annotations

import argparse

from eligible.eval.n2c2 import N2C2Classifier, load_records, score
from eligible.eval.n2c2.criteria import CRITERIA_CODES


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="dir of n2c2 XML records")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    records = load_records(args.data)
    if args.limit:
        records = records[: args.limit]
    if not records:
        raise SystemExit(f"no .xml records found in {args.data}")

    clf = N2C2Classifier()
    golds, preds = [], []
    for i, r in enumerate(records, 1):
        preds.append(clf.classify(r.text))
        golds.append(r.gold)
        print(f"[{i}/{len(records)}] {r.patient_id} classified")

    report = score(golds, preds, CRITERIA_CODES)
    print("\n" + report.to_table())


if __name__ == "__main__":
    main()
