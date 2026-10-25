# ADR 0001, OMOP CDM as the canonical clinical model

**Status:** Accepted

## Context

Eligible ingests patient data from heterogeneous sources (Synthea FHIR bundles, a legacy-schema CSV, and free-text notes) and must match it against trial eligibility criteria. The matching layer needs *one* stable representation of a patient to reason over. We have to decide what that representation is.

Candidates:
1. **Match directly against raw FHIR** from each source.
2. **Invent a bespoke internal patient schema.**
3. **Harmonize everything into OMOP CDM** (OHDSI Common Data Model) and match against that.

## Decision

Harmonize all sources into **OMOP CDM**, with standard vocabularies (SNOMED CT for conditions, RxNorm for drugs, LOINC for labs) resolved via OHDSI Athena. Nothing downstream reads a raw source directly.

## Rationale

- **Source heterogeneity is the whole point.** The FDE-signature skill this project demonstrates is mapping arbitrary client silos to one ontology. Matching against raw FHIR would dodge exactly the hard, valuable part.
- **Vocabulary normalization is mandatory anyway.** Local codes must resolve to standard concepts to evaluate criteria like "eGFR < 30" or "prior anthracycline exposure." OMOP's vocabulary tables are purpose-built for this; a bespoke schema would reinvent them badly.
- **It is the industry lingua franca** for observational/real-world data and clinical-trial cohort work, credible to the exact audience (Palantir, Tempus) this project targets, and it gives us a defensible, documented target instead of a homegrown one.
- **Lineage and reproducibility** required for a compliance story map cleanly onto dbt models over OMOP tables.

## Consequences

- We take on an upfront mapping cost (source → OMOP) and a dependency on Athena vocabulary downloads.
- The matching layer gets a single, well-documented contract to code against; sources can be added later without touching downstream logic.
- Trial output is serialized to FHIR/mCODE at the *edge* (for interoperability), while the *internal* reasoning substrate stays OMOP, the two standards serve different jobs and we use each where it fits.

## Alternatives rejected

- **Raw FHIR matching**, skips harmonization, the most valuable demonstration, and still wouldn't solve vocabulary normalization.
- **Bespoke schema**, no ecosystem, no vocabularies, not credible to the target audience.
