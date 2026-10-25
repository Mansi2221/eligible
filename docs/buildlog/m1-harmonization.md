# M1, Harmonization (messy sources → OMOP CDM)


## Goal

Take two deliberately heterogeneous clinical sources and land them in one
canonical model (OMOP CDM), with vocabulary resolution and data-quality tests.
This is the "parachute into a client's chaos and map arbitrary silos to one
ontology" demonstration, the FDE-signature move.

## What I built

**Sources (intentionally heterogeneous):**
- **Synthea FHIR R4**, 115 synthetic patients (pre-generated sample, no Java
  needed to start). Native SNOMED / LOINC / RxNorm coding.
- **Legacy hospital CSV**, an *independent* 25-patient diagnosis export in a
  different schema: ICD-10 codes, free-text sex (`M`/`Female`/` m `), US-style
  dates (`MM/DD/YYYY`, `M-D-YYYY`), noisy race, whitespace, missing cells.

**Pipeline:**
- `ingestion/synthea/parse_fhir.py`, parses FHIR bundles → `raw.synthea_*`
  tables in DuckDB. Drops name/address/telecom (no PHI-shaped fields into the
  model). Measurements scoped to lab + vital-sign numerics.
- `ingestion/legacy_csv/generate_legacy.py`, emits the messy CSV.
- **dbt (duckdb):** `staging/` normalizes each source (sex, dates, casing,
  vocab), `omop/` unions them into `person`, `condition_occurrence`,
  `drug_exposure`, `measurement`. ICD-10 → SNOMED via the `icd10_to_standard`
  seed (stand-in for OHDSI Athena until the vocab is loaded).

## Results (real numbers)

| OMOP table | rows | note |
|---|---|---|
| person | 140 | 115 synthea + 25 legacy, unified |
| condition_occurrence | 4,881 | 4,822 SNOMED + 59 ICD-10→SNOMED |
| drug_exposure | 5,869 | RxNorm |
| measurement | 58,154 | LOINC labs + vitals |

- **15 dbt data tests pass**, uniqueness, not-null, accepted values
  (gender ∈ {MALE, FEMALE}), and referential integrity (every clinical row's
  `person_id` exists in `person`).
- Crosswalk verified: `ANEMIA`/`anemia`/`Anemia` free-text all resolve to the
  same SNOMED `271737000`; `UNK`/blank race correctly nulled.

## Decisions

- **DuckDB for local dev instead of Dockerized Postgres**, no local Docker/JDK
  available, and DuckDB is zero-infra + reproducible. dbt makes the warehouse
  target swappable, so Postgres stays the documented prod target. See
  [ADR 0002](../adr/0002-duckdb-dev-postgres-prod.md).
- **Legacy source is an independent population.** Cross-source entity
  resolution (deduping the same real person across hospitals) is explicitly out
  of scope for M1, flagged as a future module, not silently skipped.
- **Curated crosswalk, not full Athena.** The 10-row ICD-10↔SNOMED seed proves
  the mechanism; loading the full OHDSI vocabulary (gated download) is a later
  step. `condition_concept_code` null would flag any unmapped legacy code.

## Known limitations / next

- Full OMOP vocabulary (Athena) not yet loaded, concept_ids are represented by
  standard source codes for now.
- PySpark ingestion path is wired but unvalidated (needs a JDK); for a
  115-patient cohort, pandas is the right tool and Spark would be theater.
- Additional real-world sources (e.g. MIMIC-IV) can slot in here as further ingestion sources.

Reproduce: `make synthea-data && make all`.

## Next (M2)

ClinicalTrials.gov ingestion + LLM eligibility-criteria parser + PHI redaction
middleware. Push repo to GitHub now that harmonization is real.
