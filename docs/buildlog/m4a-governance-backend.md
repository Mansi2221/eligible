# M4a, Governance backend (audit, FHIR, API, RBAC)


## Goal

Make the decision pipeline API-accessible, access-controlled, and
tamper-evidently audited, before putting a UI on it. This is the "safe to
deploy in a regulated environment" layer.

## What I built

**FHIR serialization** (`eligible/matching/fhir.py`)
- `TrialMatch` → FHIR `ResearchSubject` (status eligible/ineligible/candidate),
  with each criterion verdict carried as an extension. `to_bundle` wraps a
  patient's matches in a FHIR searchset Bundle. Output is FHIR; the internal
  substrate stays OMOP (ADR 0001).

**Persistent audit chain** (`eligible/audit/store.py`)
- `FileAuditLog` wraps the M0 in-memory hash chain with append-only JSONL
  persistence: reloads and re-verifies the full chain on startup. This is what
  survives restarts and lets an auditor prove no history was altered.

**FastAPI + RBAC** (`eligible/api/`)
- JWT bearer auth (`auth.py`) with a 3-role hierarchy
  (data_analyst < coordinator < physician). `require_role` enforces RBAC.
- Endpoints: `/token` (demo issuer, stands in for OIDC), `/patients/{id}/profile`
  (analyst+), `/match` (coordinator+, runs the pipeline and logs every decision
  to the chain), `/review` (physician-only human sign-off → chain), `/audit/verify`.

## Verified

- **17 unit tests** total pass (added 6 API tests: RBAC denial, match auditing,
  physician-only review, chain integrity, all with fakes, no keys).
- **Live integration** against the real DB: `/patients/4/profile` returns the
  legacy-source T2D patient; `/audit/verify` reports intact; an analyst token is
  correctly **403'd** from `/match`.

## Decisions

- **Audit is append-only JSONL, not a DB table.** A relational log is editable by
  a DBA; the hash-chained file is tamper-evident by construction. It can move to
  a WORM store in production without changing the interface.
- **Match logging captures the reasoning trace.** The pro+thinking
  `reasoning_content` is written into the audit entry, the justification an
  auditor needs for why a patient was ruled in or out.
- **Demo token issuer is explicit.** `/token` is clearly a stand-in for an OIDC
  IdP; only verification logic would run in production.

## Next (M4b)

React/Next.js human-in-the-loop review UI: coordinator runs a match, sees
per-criterion verdicts + evidence, and a physician approves/rejects, each
action hitting `/review` and landing in the audit chain.
