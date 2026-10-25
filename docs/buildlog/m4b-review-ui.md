# M4b, Human-in-the-loop review UI


## Goal

Put a real product surface on the matching pipeline: a coordinator runs a match,
a physician reviews the per-criterion evidence and approves or rejects, each
action landing in the audit chain.

## What I built

**Next.js 16 app** (`ui/`, TypeScript, App Router)
- `lib/api.ts`, typed client for the FastAPI backend: token issuance, diabetic
  patient list, run match, physician review, audit verify. Parses the FHIR
  `ResearchSubject` bundle back into a friendly per-trial shape.
- `app/page.tsx`, single review console:
  - Sign in as a role (data_analyst / coordinator / physician) → JWT.
  - Pick a patient, run the match, see each trial's decision badge
    (eligible / ineligible / needs review) and every criterion verdict with its
    met/not_met/unknown status and cited evidence.
  - Physicians get Approve / Reject buttons per trial → `/review` → audit chain.
  - "Verify audit chain" button surfaces chain integrity + entry count.
- CORS enabled on the API for the local dev origin.

## Verified

- `npm run build` compiles successfully (Turbopack). Fixed one CSS-modules
  purity error (bare `button` selector moved to `globals.css`).
- The UI talks to the same audited, RBAC-guarded API verified in M4a, the
  browser only ever sees FHIR + role-scoped endpoints.

## Result

M4 complete: the whole decision pipeline is now API-accessible, access-controlled,
tamper-evidently audited, and driveable from a product UI where a clinician makes
the final call. This is the "safe to demo in a regulated setting" milestone.

## Next (M5)

Evaluation spine: n2c2 2018 Track 1 harness → per-criterion F1 (pending DUA),
TREC Clinical Trials → nDCG, deploy, write-up.
