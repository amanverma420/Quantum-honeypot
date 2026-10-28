"""Integration tests for FastAPI REST endpoints."""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "QuantumGuard@Admin2026")

from quantum_honeypot.api.app import app
from quantum_honeypot.db.database import get_db
from quantum_honeypot.db.models import Base, Decoy, User
from quantum_honeypot.security.auth import hash_password

client = TestClient(app)
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module", autouse=True)
def init_test_environment():
    Base.metadata.create_all(bind=test_engine)
    with TestingSessionLocal() as db:
        db.add(User(
            id="test-admin",
            username="admin",
            password_hash=hash_password("QuantumGuard@Admin2026"),
            role="admin",
        ))
        db.add(User(
            id="test-viewer",
            username="viewer",
            password_hash=hash_password("ViewerTestPassword!2026"),
            role="viewer",
        ))
        db.add(Decoy(
            id="test-stripe-decoy",
            name="Synthetic Stripe Decoy",
            decoy_type="api_key",
            target_service="Stripe API Gateway",
            token_id="qtok_stripe_live_prod",
            secret_hash="test-only",
            status="ARMED",
        ))
        db.commit()
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)

def test_healthz_and_readyz():
    res_health = client.get("/healthz")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "HEALTHY"

    res_ready = client.get("/readyz")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "READY"

def test_favicon_returns_empty_no_content_response():
    response = client.get("/favicon.ico")
    assert response.status_code == 204
    assert response.content == b""

def test_unauthenticated_protected_endpoint():
    # Attempting to acknowledge alert without token must return 401
    res = client.post("/api/v1/soc/alerts/fake-id/ack")
    assert res.status_code == 401
    assert client.get("/api/v1/soc/overview").status_code == 401
    assert client.get("/api/v1/soc/events").status_code == 401
    assert client.get("/api/v1/soc/decoys").status_code == 401
    assert client.get("/api/v1/soc/stream").status_code == 401

def test_login_and_authenticated_flow():
    # Login as admin
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "QuantumGuard@Admin2026"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Query me
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "admin"
    assert me_res.json()["role"] == "admin"

    # Query SOC overview
    overview_res = client.get("/api/v1/soc/overview", headers=headers)
    assert overview_res.status_code == 200
    data = overview_res.json()
    assert "total_events" in data
    assert "critical_alerts" in data
    assert "active_decoys" in data
    assert data["system_health"] == "OPERATIONAL"

    # Trigger synthetic test breach drill
    sim_res = client.post(
        "/api/v1/soc/decoys/simulate-breach",
        headers=headers,
        params={"token_id": "qtok_stripe_live_prod", "source_ip": "10.0.0.99"}
    )
    assert sim_res.status_code == 200
    assert sim_res.json()["status"] == "SUCCESS"
    assert sim_res.json()["alert_generated"] is not None

def test_quantum_api_endpoints():
    # Bloch state
    bloch_res = client.post(
        "/api/v1/quantum/bloch",
        json={"theta": 1.5707963, "phi": 0.0, "apply_gate": "H"}
    )
    assert bloch_res.status_code == 200
    assert "probabilities" in bloch_res.json()
    assert "bloch_coordinates" in bloch_res.json()

    # Circuit simulation (Bell state)
    circ_res = client.post(
        "/api/v1/quantum/circuit",
        json={
            "qubits": 2,
            "gates": [{"gate": "H", "target": 0}, {"gate": "CNOT", "control": 0, "target": 1}],
            "shots": 500
        }
    )
    assert circ_res.status_code == 200
    counts = circ_res.json()["counts"]
    assert "00" in counts or "11" in counts

    # Bell CHSH
    chsh_res = client.post("/api/v1/quantum/bell-chsh", json={"trials": 500})
    assert chsh_res.status_code == 200
    assert chsh_res.json()["chsh_parameter_S"] > 2.0

    # BB84 QKD
    bb84_res = client.post(
        "/api/v1/quantum/bb84",
        json={"num_bits": 32, "eve_intercept": True, "noise_rate": 0.0}
    )
    assert bb84_res.status_code == 200
    assert bb84_res.json()["eve_intercepted"] is True

    # Grover search
    grover_res = client.post(
        "/api/v1/quantum/grover",
        json={"num_qubits": 3, "target_state": 3}
    )
    assert grover_res.status_code == 200
    assert grover_res.json()["success_probability"] > 0.80

    # No-cloning
    nocloning_res = client.get("/api/v1/quantum/no-cloning")
    assert nocloning_res.status_code == 200
    assert nocloning_res.json()["uqcm_theoretical_bound"] == 0.8333


def test_advanced_quantum_endpoints():
    bell = client.post("/api/v1/quantum/bell-state", json={"shots": 128, "seed": 1})
    assert bell.status_code == 200
    assert bell.json()["concurrence"] == pytest.approx(1.0, abs=1e-12)

    noise = client.post(
        "/api/v1/quantum/noise",
        json={"channel": "phase_damping", "probability": 0.4, "theta": 1.2, "phi": 0.7},
    )
    assert noise.status_code == 200
    assert noise.json()["trace"] == pytest.approx(1.0)
    assert noise.json()["purity"] < 1.0

    teleport = client.post(
        "/api/v1/quantum/teleportation",
        json={"theta": 1.2, "phi": 0.7},
    )
    assert teleport.status_code == 200
    assert teleport.json()["fidelity"] == pytest.approx(1.0, abs=1e-10)

    benchmark = client.post(
        "/api/v1/quantum/grover/benchmark",
        json={"num_qubits": 3, "marked_states": [1, 5], "trials": 100, "seed": 12},
    )
    assert benchmark.status_code == 200
    assert benchmark.json()["marked_item_count"] == 2
    assert benchmark.json()["theoretical_success_probability"] == pytest.approx(1.0, abs=1e-10)

    invalid_gate = client.post(
        "/api/v1/quantum/circuit",
        json={"qubits": 2, "gates": [{"gate": "INVALID", "target": 0}], "shots": 100},
    )
    assert invalid_gate.status_code == 422
    invalid_target = client.post(
        "/api/v1/quantum/grover",
        json={"num_qubits": 2, "target_state": 4},
    )
    assert invalid_target.status_code == 422


def test_viewer_cannot_trigger_privileged_demo():
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "viewer", "password": "ViewerTestPassword!2026"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.post("/api/v1/soc/decoys/simulate-breach", headers=headers)
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("scenario", "source_ip"),
    [
        ("honeytoken", "198.51.100.121"),
        ("api_recon", "198.51.100.122"),
        ("canary", "198.51.100.123"),
    ],
)
def test_demo_run_uses_pipeline_and_resets_only_run_data(scenario, source_ip):
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "QuantumGuard@Admin2026"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    run = client.post(
        "/api/v1/soc/decoys/simulate-breach",
        params={"scenario": scenario, "source_ip": source_ip},
        headers=headers,
    )
    assert run.status_code == 200
    data = run.json()
    assert data["synthetic"] is True
    assert data["duplicate"] is False
    assert data["demo_run_id"]
    assert data["alert_generated"] is not None
    assert data["incident_id"] is not None
    duplicate = client.post(
        "/api/v1/soc/decoys/simulate-breach",
        params={
            "scenario": scenario,
            "source_ip": source_ip,
            "demo_run_id": data["demo_run_id"],
        },
        headers=headers,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["event_id"] == data["event_id"]

    event_list = client.get(
        f"/api/v1/soc/events?source_ip={source_ip}",
        headers=headers,
    ).json()
    assert any(event["id"] == data["event_id"] for event in event_list["events"])

    reset = client.delete(
        f"/api/v1/soc/demo/runs/{data['demo_run_id']}",
        headers=headers,
    )
    assert reset.status_code == 200
    assert reset.json()["events_removed"] == 1
    assert reset.json()["audit_preserved"] is True
    after_reset = client.get(
        f"/api/v1/soc/events?source_ip={source_ip}",
        headers=headers,
    ).json()
    assert all(event["id"] != data["event_id"] for event in after_reset["events"])
