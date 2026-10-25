# Eligible, Build Plan

Living build sheet. Checked off as milestones land. The "why" behind each decision goes in `docs/buildlog/` and `docs/adr/`.

## Locked decisions

- **Name:** Eligible (slug `eligible`)
- **Data:** n2c2 2018 Track 1 (benchmark) + Synthea (synthetic patients)
- **UI:** React / Next.js
- **LLM:** DeepSeek V4 Pro API (pro + thinking mode for matching; flash for extraction). Model IDs are env-configurable.
- **Docs:** live build log + ADRs

## Target output & benchmarks

- Match output serialized as HL7 FHIR / mCODE.
- **n2c2 2018 Track 1 Cohort Selection**, per-criterion F1, micro/macro.
- **TREC Clinical Trials Track**, nDCG@10, P@10.
- Report failure modes, not just headline numbers.

## Data access checklist (start day one)

- [ ] **n2c2 2018 Track 1 DUA**, Harvard DBMI Data Portal. *Long pole, apply first.*
- [ ] OHDSI Athena vocabularies (SNOMED / RxNorm / LOINC)
- [ ] TREC Clinical Trials qrels + corpus snapshot
- [ ] Synthea (generate locally)
- [ ] ClinicalTrials.gov API v2 (no key)
- [ ] DeepSeek API key + credit
- [ ] Pinecone + Neon/Supabase Postgres

## Milestones

### M0, Foundations  *(in progress)*
- [x] Git repo + directory skeleton
- [x] README, PLAN, docs scaffold (buildlog + ADR + architecture)
- [x] Cache-aware DeepSeek client + prompt assembly
- [x] Merkle audit-chain primitive
- [x] `.env.example`, `pyproject.toml`, `docker-compose.yml`
- [ ] Obtain n2c2 DUA approval

### M1, Harmonization  *(complete)*
- [x] Synthea FHIR R4 cohort (115 patients) parsed → raw tables
- [x] Deliberately messy legacy-schema CSV (25 patients, ICD-10, dirty)
- [x] OMOP CDM in DuckDB (dev), Postgres kept as prod target (ADR 0002)
- [x] dbt staging + OMOP models, ICD-10→SNOMED crosswalk (Athena stand-in seed)
- [x] Data-quality checks + referential integrity (15 dbt tests pass)
- [ ] **→ push repo to GitHub (now due)**
- [ ] Later: load full OHDSI Athena vocab; validate PySpark path (needs JDK)

### M2, Trials + criteria structuring  *(mostly complete)*
- [x] ClinicalTrials.gov v2 ingestion (30 real diabetes trials → raw.trials)
- [x] LLM eligibility parser → structured criteria schema (pydantic); unit-tested
- [x] PHI redaction middleware (regex + optional NER), 4 tests
- [ ] Live criteria parse (`make criteria`), pending DEEPSEEK_API_KEY

### M3, Matching engine  *(complete, live-verified)*
- [x] Pinecone integrated embeddings + BGE reranker (30 trials indexed)
- [x] LangGraph pipeline: phenotype → retrieve → match
- [x] Per-criterion pro+thinking verdicts with cited evidence + decision rule
- [x] Live end-to-end run on real diabetic patients (incl. cross-source legacy patient)
- [ ] FHIR/mCODE serialization of the match result (moved to M4)

### M4, Governance + serving  *(backend done)*
- [x] FastAPI + JWT/RBAC (3-role hierarchy), demo OIDC-style token issuer
- [x] Merkle audit chain persisted (JSONL) + wired to match + review endpoints
- [x] FHIR ResearchSubject/Bundle serialization of match results
- [x] Backend live-verified (17 tests; real profile + audit + RBAC checks)
- [x] Next.js human-in-the-loop review UI (M4b), builds clean, RBAC-driven, audit-wired

### M5, Evaluation + polish  *(harness built; data pending)*
- [x] n2c2 harness (loader + pro+thinking classifier + F1 scorer), 25 tests, live-verified on fixture
- [ ] Run on real n2c2 test set → headline F1 (blocked on DUA data)
- [ ] TREC CT harness → nDCG@10
- [ ] Deploy demo
