"""HTTP-level tests against the FastAPI app (stub mode, hermetic store)."""
import pytest
from fastapi.testclient import TestClient

import app.main as m
from app.store import ProposalStore


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "store", ProposalStore(tmp_path / "api.db"))
    return TestClient(m.app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] and body["mode"] in ("stub", "live")
    assert body["inspections"] > 1000


def test_run_batch_and_bounds(client):
    assert client.post("/api/run?batch=0").status_code == 400
    assert client.post("/api/run?batch=99").status_code == 400
    r = client.post("/api/run?batch=3")
    assert r.status_code == 200
    body = r.json()
    assert len(body["processed"]) == 3
    assert body["n_errors"] == 0
    assert body["remaining"] > 0


def test_decide_flow_and_finality(client):
    client.post("/api/run?batch=5")
    props = client.get("/api/proposals?status=proposed").json()["proposals"]
    assert props
    pid = props[0]["proposal_id"]
    assert client.post(f"/api/proposals/{pid}/decide",
                       json={"decision": "approved"}).status_code == 200
    assert client.post(f"/api/proposals/{pid}/decide",
                       json={"decision": "rejected"}).status_code == 409
    auto = [p for p in client.get("/api/proposals").json()["proposals"]
            if p["status"] == "auto_approved"]
    for p in auto[:1]:
        assert client.post(f"/api/proposals/{p['proposal_id']}/decide",
                           json={"decision": "approved"}).status_code == 409
    assert client.get("/api/stats").json()["pending"] >= 0


def test_decide_body_validation(client):
    client.post("/api/run?batch=1")
    pid = client.get("/api/proposals").json()["proposals"][0]["proposal_id"]
    assert client.post(f"/api/proposals/{pid}/decide",
                       json={"decision": "maybe"}).status_code == 422
    assert client.post(f"/api/proposals/{pid}/decide",
                       json={"decision": "approved", "decided_by": "<script>"}).status_code == 422


def test_inspection_record(client):
    client.post("/api/run?batch=1")
    iid = client.get("/api/proposals").json()["proposals"][0]["inspection_id"]
    r = client.get(f"/api/inspections/{iid}/record")
    assert r.status_code == 200
    assert "VIOLATIONS" in r.json()["text"]
    assert client.get("/api/inspections/0/record").status_code == 404


def test_schedule_from_approved(client):
    client.post("/api/run?batch=8")
    props = client.get("/api/proposals?status=proposed").json()["proposals"]
    recheck = [p for p in props if p["action_type"] == "schedule_reinspection"]
    if not recheck:
        pytest.skip("no reinspection proposals in this stub batch")
    client.post(f"/api/proposals/{recheck[0]['proposal_id']}/decide",
                json={"decision": "approved"})
    rows = client.get("/api/schedule").json()["schedule"]
    assert rows and rows[0]["due_date"] and rows[0]["window_days"] >= 3
