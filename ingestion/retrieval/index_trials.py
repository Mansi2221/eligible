"""Index trials into Pinecone for candidate retrieval.

Builds one text record per trial (title + conditions + a criteria digest) and
upserts it via Pinecone integrated embeddings. Requires PINECONE_API_KEY.

Run:  python ingestion/retrieval/index_trials.py
"""

from __future__ import annotations

import os

import duckdb

from eligible.retrieval.vector_store import TrialRetriever

DB_PATH = os.environ.get("ELIGIBLE_DB", "data/eligible.duckdb")


def main() -> None:
    con = duckdb.connect(DB_PATH, read_only=True)
    trials = con.execute(
        "SELECT nct_id, brief_title, conditions, sex, min_age, max_age FROM raw.trials"
    ).fetchall()
    digests = dict(
        con.execute(
            """SELECT nct_id, string_agg(text, ' | ') FROM raw.trial_criteria GROUP BY 1"""
        ).fetchall()
    )
    con.close()

    records = []
    for nct_id, title, conditions, sex, min_age, max_age in trials:
        digest = (digests.get(nct_id) or "")[:1500]
        records.append(
            {
                "nct_id": nct_id,
                "chunk_text": f"{title}. Conditions: {conditions}. Eligibility: {digest}",
                "metadata": {
                    "sex": sex or "ALL",
                    "min_age": min_age or "",
                    "max_age": max_age or "",
                },
            }
        )

    n = TrialRetriever().index_trials(records)
    print(f"indexed {n} trials into Pinecone")


if __name__ == "__main__":
    main()
