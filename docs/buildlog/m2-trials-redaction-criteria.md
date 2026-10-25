# M2, Trials ingestion, PHI redaction, criteria parser


## Goal

Bring in the trial side of the match and the two components that gate every LLM
call: a structured representation of eligibility criteria, and the PHI redaction
that sanitizes patient text before it leaves the local network.

## What I built

**ClinicalTrials.gov ingestion** (`ingestion/clinicaltrials/fetch_trials.py`)
- Pulls trials + eligibility from the public API v2 (no key). Handles
  pagination, keeps only trials with eligibility text, lands them in
  `raw.trials`. Fetched **30 real recruiting Type 2 Diabetes trials** as the
  starter corpus (sex/age/healthy-volunteer fields + free-text criteria).

**PHI redaction middleware** (`eligible/redaction/`)
- Hybrid design: a regex layer for structured identifiers (SSN, MRN, phone,
  email, URL, IP, dates, ZIP) plus an *optional* spaCy NER layer for names /
  locations that degrades gracefully to regex-only when no model is installed.
- Deterministic surrogate tokens (`[PHONE_1]`, `[PATIENT_NAME_1]`), the same
  value always maps to the same token, so redacted text stays coherent.
- Overlap resolution keeps the earliest, longest match. 4 unit tests.

**Eligibility criteria parser** (`eligible/criteria/`)
- Pydantic schema (`Criterion` / `ParsedEligibility`): each atomic criterion has
  kind (inclusion/exclusion), category, attribute, operator, value, unit,
  temporal window, machine-checkable, so the matcher evaluates structure
  instead of re-reading prose per patient.
- `CriteriaParser` uses the flash tier + a cache-aware prompt (stable
  system+schema prefix, variable trial text last). Structure verified with a
  fake-client unit test (no key needed); runs live once the key is in `.env`.
- `ingestion/clinicaltrials/parse_criteria.py` runs it over `raw.trials` →
  `raw.trial_criteria`.

## Status

- **11 Python unit tests pass** (audit chain, redaction, criteria parser).
- ClinicalTrials.gov ingestion + redaction are fully live and verified.
- The LLM criteria parse is built and unit-tested but **not yet run live**, it
  needs `DEEPSEEK_API_KEY`. `make criteria` runs it when the key is set.

## Decisions

- **Redaction is regex-first, NER-optional.** Structured identifiers are the
  high-precision, zero-dependency win; the spaCy layer is additive and doesn't
  block the pipeline if a model isn't installed. Keeps M2 runnable now.
- **Criteria are parsed once per trial, not per patient.** Structured criteria
  are cached in `raw.trial_criteria`; matching reuses them across all patients,
  which is also what makes DeepSeek context-caching pay off.

## Next (M3)

Vector fabric (Pinecone parent-child + reranker) + LangGraph matching agents
(Phenotype / Retrieval / Matching) → per-criterion verdicts with evidence →
FHIR/mCODE. Needs DeepSeek + Pinecone keys.
