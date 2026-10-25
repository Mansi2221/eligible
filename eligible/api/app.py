"""FastAPI serving layer for Eligible.

Endpoints are guarded by JWT + RBAC. Every match decision and human review is
written to the tamper-evident audit chain. Run:

    uvicorn eligible.api.app:app --reload
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from eligible import __version__
from eligible.api.auth import User, issue_token, require_role
from eligible.audit import FileAuditLog
from eligible.config import get_settings
from eligible.matching.fhir import to_bundle, to_research_subject
from eligible.matching.phenotype import PhenotypeBuilder

app = FastAPI(title="Eligible", version=__version__)

# Allow the local Next.js dev server to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- injectable dependencies (overridden in tests) ---
@lru_cache
def get_audit() -> FileAuditLog:
    return FileAuditLog(get_settings().audit_log_path)


@lru_cache
def get_phenotype_builder() -> PhenotypeBuilder:
    return PhenotypeBuilder()


def get_pipeline():
    from eligible.matching import MatchingPipeline

    return MatchingPipeline()


# --- request models ---
class TokenRequest(BaseModel):
    username: str
    role: str  # data_analyst | coordinator | physician


class MatchRequest(BaseModel):
    person_id: int


class ReviewRequest(BaseModel):
    person_id: int
    nct_id: str
    approved: bool
    note: str | None = None


# --- routes ---
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.post("/token")
def token(req: TokenRequest) -> dict:
    """Demo token issuer (stands in for an OIDC IdP)."""
    return {"access_token": issue_token(req.username, req.role), "token_type": "bearer"}


@app.get("/patients/diabetic")
def diabetic_patients(
    user: User = Depends(require_role("data_analyst")),
    builder: PhenotypeBuilder = Depends(get_phenotype_builder),
) -> dict:
    """A small demo cohort of patients with a T2D diagnosis, for the picker."""
    return {"person_ids": builder.diabetic_cohort(limit=10)}


@app.get("/patients/{person_id}/profile")
def patient_profile(
    person_id: int,
    user: User = Depends(require_role("data_analyst")),
    builder: PhenotypeBuilder = Depends(get_phenotype_builder),
) -> dict:
    return builder.build(person_id).model_dump()


@app.post("/match")
def match(
    req: MatchRequest,
    user: User = Depends(require_role("coordinator")),
    pipeline=Depends(get_pipeline),
    audit: FileAuditLog = Depends(get_audit),
) -> dict:
    matches = pipeline.run(req.person_id)
    for m in matches:
        audit.append(
            "match_decision",
            {
                "person_id": m.person_id,
                "nct_id": m.nct_id,
                "decision": m.decision,
                "actor": user.sub,
                "verdicts": [v.model_dump() for v in m.verdicts],
                "reasoning": m.reasoning,
            },
        )
    return to_bundle(matches)


@app.post("/review")
def review(
    req: ReviewRequest,
    user: User = Depends(require_role("physician")),
    audit: FileAuditLog = Depends(get_audit),
) -> dict:
    """Human-in-the-loop sign-off, physician only. Committed to the audit chain."""
    entry = audit.append(
        "human_review",
        {
            "person_id": req.person_id,
            "nct_id": req.nct_id,
            "approved": req.approved,
            "reviewer": user.sub,
            "note": req.note,
        },
    )
    return {"logged": True, "index": entry.index, "hash": entry.entry_hash}


@app.get("/audit/verify")
def audit_verify(
    user: User = Depends(require_role("data_analyst")),
    audit: FileAuditLog = Depends(get_audit),
) -> dict:
    broken = audit.verify()
    return {"intact": broken is None, "broken_index": broken, "length": len(audit)}
