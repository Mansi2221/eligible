# M5, n2c2 evaluation harness


## Goal

The defensibility spine: score the matcher against a published, gold-labeled
benchmark so the project reports real F1, not vibes. Built now; runs the moment
the n2c2 DUA clears.

## What I built

**n2c2 2018 Track 1 harness** (`eligible/eval/n2c2/`)
- `criteria.py`, the 13 official cohort-selection criteria with their
  annotation-guideline definitions.
- `loader.py`, parse the shared-task XML (record text in `<TEXT>`, gold labels
  in `<TAGS>`) into `N2C2Record`s.
- `classifier.py`, one pro+thinking call per patient: the 13 definitions form
  the cached prompt prefix, the record is appended last; returns met/not met per
  criterion. Same adjudication the trial matcher does, pointed at the benchmark.
- `score.py`, per-criterion precision/recall/F1 (positive = `met`), plus
  micro-F1 (the task's primary metric) and macro-F1.
- `eval/n2c2/run.py`, end-to-end runner (`--data <dir> [--limit N]`).

## Verified

- **25 unit tests pass** (added loader + scoring: exact tp/fp/fn/F1 math, all-13
  label parsing, perfect-prediction sanity).
- **Live end-to-end run** on a synthetic gold-labeled fixture: the classifier
  correctly labeled all five `met` criteria from free text → **micro-F1 1.000**.
  (Macro is sensitive to sparse-positive criteria on a 1-record sample; moot on
  the full 86-record test set where every criterion has positives.)

## Status: ready, waiting on data

The only missing input is the **n2c2 2018 Track 1 data**, gated behind the DUA.
Once the records are under `data/n2c2/test/`, one command produces the numbers:

```bash
python eval/n2c2/run.py --data data/n2c2/test
```

## Metric note

`met` is the positive class. Micro-F1 pools all criterion instances (the
shared-task ranking metric); macro-F1 averages per-criterion F1. Per-criterion
F1 for a criterion with no positive gold instances is 0 by definition, only
relevant on tiny samples.

## Next

- Run against real n2c2 test set → headline F1 (post-DUA).
- TREC Clinical Trials harness (nDCG@10) for the retrieval side.
- Deploy demo + results write-up.
