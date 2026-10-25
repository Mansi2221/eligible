# M0, Foundations


## Goal

Stand up the skeleton, the documentation habit, and the two primitives everything else depends on (the LLM client and the audit chain), before writing a line of domain logic.

## What I built

- Git repo + directory skeleton mirroring the layer architecture (ingestion → transform → matching → governance → eval).
- `README.md`, `PLAN.md`, and this `docs/` tree (build log + ADRs + architecture). The rule from here on: **the build log is written as the work happens, not reconstructed.**
- **Cache-aware DeepSeek client** (`eligible/llm/`). OpenAI-compatible, two model tiers (flash for extraction, pro + thinking mode for reasoning), model IDs env-configurable. Prompt assembly deliberately orders messages *stable-prefix first, variable-suffix last* so that reused content (schemas, trial protocols, system instructions) hits the provider's context cache.
- **Merkle audit-chain primitive** (`eligible/audit/`). Each entry stores the SHA-256 of the previous entry; `verify_chain()` walks the log and flags the first broken link. This is the spine of the compliance story, so it exists from commit one rather than being bolted on at the end.
- Config (`pyproject.toml`, `.env.example`, `docker-compose.yml` for Postgres).

## Decisions

- **OMOP as the canonical model** rather than matching against raw FHIR. Recorded in [ADR 0001](../adr/0001-omop-as-canonical-model.md).
- **Model tiering via env, not hardcoding.** The exact DeepSeek V4 model IDs are set through env vars so the code doesn't rot when model names change and the routing (flash vs pro) stays a config concern, not a code one.
- **Audit + redaction are primitives, not features.** Building them first forces every later component to be wired through them, instead of retrofitting governance onto a system that already leaks.

## Open items

- n2c2 2018 Track 1 DUA still needs to be filed (long pole for the eval spine).
- Next.js UI is a placeholder dir; it gets scaffolded with `create-next-app` in M4.

## Next (M1)

Generate a Synthea cohort, derive a deliberately messy legacy-schema CSV from it, and land the two in OMOP CDM via dbt with vocabulary mapping. Push the repo to GitHub once M1 is real.
