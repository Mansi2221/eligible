# Eligible, Architecture

Living document. Updated as the system takes shape.

## Design thesis

An enterprise client's data is chaotic and their question is precise. Eligible mirrors how a Forward Deployed Engineer actually delivers: build a **platform** that harmonizes arbitrary source data into one canonical model, then run a **use case** on top of that model. Here the canonical model is OMOP CDM and the use case is patient-to-trial matching.

## Data flow

```
                        ┌─────────────────────────────────────────────┐
  Synthea FHIR ───┐     │              HARMONIZATION                    │
  Legacy CSV ─────┼───► │  PySpark ingest → dbt staging → OMOP CDM      │
  (free-text) ────┘     │  (SNOMED / RxNorm / LOINC via Athena)         │
                        └───────────────────────┬─────────────────────┘
                                                 │ canonical patient
                                                 ▼
  ClinicalTrials.gov ──► criteria parser ──► structured eligibility logic
        (API v2)          (LLM, flash)              │
                                                    ▼
                        ┌─────────────────────────────────────────────┐
                        │                MATCHING                       │
                        │  Phenotype agent → Retrieval (Pinecone p/c +  │
                        │  reranker) → Matching agent (pro + thinking)  │
                        │  → per-criterion verdict + evidence           │
                        └───────────────────────┬─────────────────────┘
                                                 ▼
                                    FHIR / mCODE match result
                                                 │
        ┌────────────────────────────────────────┼───────────────────────┐
        │ GOVERNANCE (cross-cutting)              ▼                        │
        │  PHI redaction before every LLM call · FastAPI RBAC ·           │
        │  SHA-256 Merkle audit chain · human-in-the-loop review (Next.js)│
        └────────────────────────────────────────────────────────────────┘
                                                 │
                                                 ▼
                          EVALUATION: n2c2 (F1) · TREC CT (nDCG@10)
```

## Component map

| Package / dir | Role |
|---|---|
| `ingestion/` | Source loaders (Synthea, legacy CSV, ClinicalTrials.gov) + PySpark jobs |
| `transform/` | dbt project → OMOP CDM (staging + omop models) |
| `eligible/llm/` | DeepSeek client + cache-aware prompt assembly |
| `eligible/criteria/` | Eligibility free-text → structured logic |
| `eligible/retrieval/` | Pinecone parent-child index + reranker |
| `eligible/matching/` | LangGraph agents, per-criterion reasoning, FHIR/mCODE output |
| `eligible/redaction/` | PHI redaction middleware (regex + NER) |
| `eligible/audit/` | SHA-256 Merkle hash-chain audit log |
| `eligible/api/` | FastAPI app, OIDC/JWT RBAC |
| `ui/` | Next.js human-in-the-loop review interface |
| `eval/` | n2c2 + TREC benchmark harnesses |

## Key principles

1. **OMOP is the single source of truth.** Nothing downstream reads a raw source directly. See [ADR 0001](adr/0001-omop-as-canonical-model.md).
2. **PHI never leaves the local network un-redacted.** Redaction runs before any external API call.
3. **Every autonomous decision is auditable.** The matching agent's reasoning trace is committed to the hash chain, so an auditor can reconstruct *why* a patient was ruled in or out.
4. **Cache-aware prompting.** Stable content (schemas, protocols, instructions) goes at the prompt prefix; variable per-patient content goes last, to exploit context caching.
5. **Benchmarked, not vibes.** Correctness is measured against published gold labels.
