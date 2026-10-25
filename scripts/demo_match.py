"""End-to-end matching demo: run the pipeline on the diabetic cohort.

Requires DEEPSEEK_API_KEY + PINECONE_API_KEY, a built OMOP db, parsed criteria,
and an indexed trial set. Run:  python scripts/demo_match.py [--patients N]
"""

from __future__ import annotations

import argparse

from eligible.matching import MatchingPipeline
from eligible.matching.phenotype import PhenotypeBuilder


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--patients", type=int, default=3)
    args = ap.parse_args()

    pipeline = MatchingPipeline()
    cohort = PhenotypeBuilder().diabetic_cohort(limit=args.patients)
    print(f"matching {len(cohort)} diabetic patients against retrieved trials\n")

    for pid in cohort:
        matches = pipeline.run(pid)
        print("=" * 72)
        print(f"PATIENT {pid}")
        for m in sorted(matches, key=lambda x: x.decision):
            print(f"  {m.nct_id}  ->  {m.decision.upper()}")
            # show up to two decisive verdicts
            decisive = [v for v in m.verdicts if v.status != "unknown"][:2]
            for v in decisive:
                print(f"      [{v.status}] ({v.kind}) {v.text[:60]}, {v.evidence[:60]}")
        print()


if __name__ == "__main__":
    main()
