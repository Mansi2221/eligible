"""Fetch clinical trials + eligibility criteria from the ClinicalTrials.gov API v2.

Public API, no key required. Lands trials into ``raw.trials`` in the same DuckDB
the patient data lives in, so the matching layer (M3) can query both together.

Run:  python ingestion/clinicaltrials/fetch_trials.py --condition "type 2 diabetes" --max 30
"""

from __future__ import annotations

import argparse
import os
import time

import duckdb
import pandas as pd
import requests

API = "https://clinicaltrials.gov/api/v2/studies"
DB_PATH = os.environ.get("ELIGIBLE_DB", "data/eligible.duckdb")

FIELDS = ",".join(
    [
        "protocolSection.identificationModule.nctId",
        "protocolSection.identificationModule.briefTitle",
        "protocolSection.conditionsModule.conditions",
        "protocolSection.eligibilityModule",
    ]
)


def fetch_studies(condition: str, max_studies: int, status: str = "RECRUITING") -> list[dict]:
    rows: list[dict] = []
    token: str | None = None
    while len(rows) < max_studies:
        params = {
            "query.cond": condition,
            "filter.overallStatus": status,
            "fields": FIELDS,
            "pageSize": min(100, max_studies - len(rows)),
        }
        if token:
            params["pageToken"] = token
        resp = requests.get(API, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for s in data.get("studies", []):
            ps = s["protocolSection"]
            idm = ps.get("identificationModule", {})
            elig = ps.get("eligibilityModule", {})
            conds = ps.get("conditionsModule", {}).get("conditions", [])
            rows.append(
                {
                    "nct_id": idm.get("nctId"),
                    "brief_title": idm.get("briefTitle"),
                    "conditions": "; ".join(conds),
                    "eligibility_criteria": elig.get("eligibilityCriteria"),
                    "sex": elig.get("sex"),
                    "min_age": elig.get("minimumAge"),
                    "max_age": elig.get("maximumAge"),
                    "healthy_volunteers": elig.get("healthyVolunteers"),
                    "std_ages": "; ".join(elig.get("stdAges", [])),
                    "query_condition": condition,
                }
            )
        token = data.get("nextPageToken")
        if not token:
            break
        time.sleep(0.3)  # be polite
    return rows[:max_studies]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", default="type 2 diabetes")
    ap.add_argument("--max", type=int, default=30)
    ap.add_argument("--status", default="RECRUITING")
    args = ap.parse_args()

    rows = fetch_studies(args.condition, args.max, args.status)
    # Keep only trials that actually have eligibility text to reason over.
    rows = [r for r in rows if r["eligibility_criteria"]]

    df = pd.DataFrame(rows)  # noqa: F841, used by duckdb below
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE TABLE IF NOT EXISTS raw.trials AS SELECT * FROM df WHERE false")
    con.execute("DELETE FROM raw.trials WHERE query_condition = ?", [args.condition])
    con.execute("INSERT INTO raw.trials SELECT * FROM df")
    n = con.execute("SELECT count(*) FROM raw.trials").fetchone()[0]
    con.close()
    print(f"fetched {len(rows)} trials for '{args.condition}' -> raw.trials (total now {n})")


if __name__ == "__main__":
    main()
