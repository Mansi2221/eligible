# Eligible

**Patient-to-trial matching on harmonized clinical data.**

Eligible answers a deceptively hard clinical question (*is this patient eligible for this trial?*) end to end. It harmonizes messy, multi-schema patient data into a canonical clinical model (OMOP CDM), structures free-text trial eligibility criteria into machine-checkable logic, and matches the two with an audited, agentic reasoning pipeline. Every decision is redacted of PHI, access-controlled, and written to a tamper-evident audit trail.

This is not a throwaway demo. The matching decisions are built to be scored against a published, gold-labeled benchmark (n2c2 2018 Cohort Selection), and the eval harness reports per-criterion F1 alongside the cases it gets wrong.

> Note: not the same as eligible.com (insurance eligibility). This is a clinical-trials matching research project.

## Why this exists

Clinical trial enrollment is one of the most expensive bottlenecks in drug development. Eligible patients are routinely missed because matching them to trials means manually cross-referencing hundred-page protocols against fragmented longitudinal records. Eligible automates the harmonize, structure, match, and govern loop that a coordinator does by hand.

## Architecture at a glance

| Layer | Responsibility |
|---|---|
| **Ingestion** | Pull heterogeneous sources: Synthea FHIR, a legacy-schema CSV, ClinicalTrials.gov trials |
| **Harmonization** | Map everything to **OMOP CDM** (SNOMED / RxNorm / LOINC) with full lineage via dbt |
| **Criteria structuring** | LLM parses trial eligibility free-text into structured, checkable logic |
| **Matching** | Agentic per-criterion reasoning (eligible / ineligible / unknown, with evidence) into FHIR/mCODE |
| **Governance** | PHI redaction, RBAC, SHA-256 Merkle audit chain, human-in-the-loop review |
| **Evaluation** | Scored on the n2c2 2018 Track 1 cohort-selection task (per-criterion F1) |

See [`docs/architecture.md`](docs/architecture.md) for the full data flow, and [`PLAN.md`](PLAN.md) for the milestone-by-milestone build sheet.

## Documentation

This project is documented as it is built. The [`docs/buildlog/`](docs/buildlog) directory is a dated engineering journal that captures decisions, tradeoffs, and dead ends. [`docs/adr/`](docs/adr) records the architectural decisions.

## Running it locally

```bash
# 1. Python env + data
python -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
make synthea-data          # download the Synthea FHIR sample
make all                   # build OMOP CDM + fetch trials
make criteria              # parse eligibility (needs DEEPSEEK_API_KEY in .env)
python ingestion/retrieval/index_trials.py   # index trials into Pinecone

# 2. API (terminal 1)
uvicorn eligible.api.app:app --reload

# 3. UI (terminal 2)
cd ui && npm install && npm run dev   # http://localhost:3000
```

## Status

The full pipeline (harmonization, criteria structuring, matching, governance, and a review UI) is built and verified end to end across milestones M0 through M5. The n2c2 benchmark harness is ready; the headline F1 number lands once the dataset's data-use agreement clears.
