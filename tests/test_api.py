"""API tests: RBAC, match auditing, human review, with fakes (no keys/LLM)."""

import pytest
from fastapi.testclient import TestClient

from eligible.api import app as appmod
from eligible.api.auth import issue_token
from eligible.audit import FileAuditLog
from eligible.matching.schema import CriterionVerdict, TrialMatch


class FakePipeline:
    def run(self, person_id: int):
        v = [
            CriterionVerdict(text="Age 18-70", kind="inclusion", status="met", evidence="age 50"),
            CriterionVerdict(text="type 1 diabetes", kind="exclusion", status="not_met", evidence="T2D"),
        ]
        return [TrialMatch(nct_id="NCT001", person_id=person_id, verdicts=v,
                           decision=TrialMatch.decide(v), reasoning="reasoned")]


@pytest.fixture
def client(tmp_path):
    audit = FileAuditLog(str(tmp_path / "audit.jsonl"))
    appmod.app.dependency_overrides[appmod.get_pipeline] = lambda: FakePipeline()
    appmod.app.dependency_overrides[appmod.get_audit] = lambda: audit
    yield TestClient(appmod.app), audit
    appmod.app.dependency_overrides.clear()


def _auth(role):
    return {"Authorization": f"Bearer {issue_token('u1', role)}"}


def test_health_open(client):
    c, _ = client
    assert c.get("/health").json()["status"] == "ok"


def test_match_requires_auth(client):
    c, _ = client
    assert c.post("/match", json={"person_id": 1}).status_code in (401, 403)


def test_analyst_cannot_match(client):
    c, _ = client
    r = c.post("/match", json={"person_id": 1}, headers=_auth("data_analyst"))
    assert r.status_code == 403


def test_coordinator_match_is_audited(client):
    c, audit = client
    r = c.post("/match", json={"person_id": 4}, headers=_auth("coordinator"))
    assert r.status_code == 200
    body = r.json()
    assert body["resourceType"] == "Bundle" and body["total"] == 1
    assert body["entry"][0]["resource"]["resourceType"] == "ResearchSubject"
    assert len(audit) == 1  # decision logged to the chain


def test_review_is_physician_only(client):
    c, _ = client
    payload = {"person_id": 4, "nct_id": "NCT001", "approved": True}
    assert c.post("/review", json=payload, headers=_auth("coordinator")).status_code == 403
    assert c.post("/review", json=payload, headers=_auth("physician")).status_code == 200


def test_audit_verify_intact(client):
    c, _ = client
    c.post("/match", json={"person_id": 4}, headers=_auth("coordinator"))
    r = c.get("/audit/verify", headers=_auth("data_analyst"))
    assert r.json()["intact"] is True
    assert r.json()["length"] >= 1
