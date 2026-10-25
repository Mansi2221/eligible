"""Parse fetched trials' free-text eligibility into structured criteria.

Reads raw.trials, runs the LLM criteria parser on each, and writes the
structured criteria to raw.trial_criteria. Requires DEEPSEEK_API_KEY in .env.

Run:  python ingestion/clinicaltrials/parse_criteria.py [--limit N]
"""

from __future__ import annotations

import argparse
import os

import duckdb
import pandas as pd

from eligible.criteria import CriteriaParser

DB_PATH = os.environ.get("ELIGIBLE_DB", "data/eligible.duckdb")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="parse only the first N trials")
    args = ap.parse_args()

    con = duckdb.connect(DB_PATH)
    trials = con.execute(
        "SELECT nct_id, eligibility_criteria FROM raw.trials"
        + (f" LIMIT {args.limit}" if args.limit else "")
    ).fetchall()

    parser = CriteriaParser()  # reads DEEPSEEK_API_KEY from env
    rows: list[dict] = []
    for nct_id, text in trials:
        parsed = parser.parse(nct_id, text)
        for c in parsed.criteria:
            rows.append({"nct_id": nct_id, **c.model_dump()})
        print(f"{nct_id}: {len(parsed.criteria):2d} criteria "
              f"({len(parsed.inclusion)} incl / {len(parsed.exclusion)} excl)")

    df = pd.DataFrame(rows)  # noqa: F841, used by duckdb below
    con.execute("CREATE OR REPLACE TABLE raw.trial_criteria AS SELECT * FROM df")
    con.close()
    print(f"\nwrote {len(rows)} structured criteria for {len(trials)} trials -> raw.trial_criteria")


if __name__ == "__main__":
    main()
