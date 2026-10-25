# M3, Matching engine (phenotype → retrieve → adjudicate)


## Goal

Turn a patient in OMOP and a trial's structured criteria into an evidence-backed
eligibility decision, via a stateful pipeline that only spends reasoning tokens
on plausible pairs.

## What I built

**Phenotype builder** (`eligible/matching/phenotype.py`)
- Deterministic OMOP → `PatientProfile` (demographics, conditions, meds, latest
  key labs/vitals). Compact `to_prompt_text()` rendering for retrieval + matching.

**Retrieval** (`eligible/retrieval/vector_store.py`)
- Pinecone integrated inference: trials embedded server-side
  (multilingual-e5-large), candidate generation by patient profile, reranked by
  a cross-encoder (bge-reranker-v2-m3). 30 trials indexed.

**Matcher** (`eligible/matching/matcher.py`)
- One **pro + thinking-mode** call per (patient, trial): adjudicates every
  criterion as met / not_met / unknown with a cited evidence phrase. The
  thinking trace (`reasoning_content`) is captured for the M4 audit log.

**LangGraph pipeline** (`eligible/matching/graph.py`)
- Stateful graph `phenotype → retrieve → match`, dependencies injected for
  testability.

**Decision rule** (`eligible/matching/schema.py`)
- Eligible iff every inclusion met and no exclusion met; any `unknown` →
  `needs_review`. Never a silent pass.

## Live result (real end-to-end run)

Patient 4, a **legacy-source** female, age 50, Type 2 diabetes (proof the
cross-source harmonization flows all the way to matching), against 5
Pinecone-retrieved trials:

```
NCT07535307 -> INELIGIBLE   [met] sex FEMALE; [met] age 50 in 18-75
NCT06203860 -> NEEDS_REVIEW [met] >18; [met] Established diagnosis of T2D
NCT05307731 -> NEEDS_REVIEW [met] age 18-70; [met] clinically diagnosed T2D
```

The verdicts are evidence-grounded ("Type 2 diabetes mellitus listed in
conditions") and correctly drop to `needs_review` when the profile lacks the
data a criterion needs (e.g. no HbA1c on file) instead of guessing.

## Decisions

- **Tiering:** flash for criteria extraction (M2), **pro + thinking for
  matching** (this milestone). Reviewed and kept, reasoning is where the
  thinking tokens earn their cost; extraction doesn't need them.
- **Retrieval before matching:** candidate generation keeps the expensive
  pro+thinking calls off implausible pairs (30 trials → top 5 per patient).
- **`unknown` is first-class:** missing data yields `needs_review`, not a
  fabricated verdict, the safe default for a clinical decision-support tool.

## Status

- 16 unit tests pass (audit, redaction, criteria, matching decision rule).
- Full pipeline verified live on real diabetic patients.
- Pinecone API surface (9.x): `upsert_records(namespace=, records=)` and
  `Hit.id/.score/.fields`, fixed during the live bring-up.

## Next (M4)

Wire the SHA-256 Merkle audit chain to every match decision; FastAPI + RBAC;
React/Next.js human-in-the-loop review UI.
