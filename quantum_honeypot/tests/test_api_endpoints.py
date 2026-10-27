"""Integration tests for FastAPI REST endpoints."""

import pytest
from fastapi.testclient import TestClient
from quantum_honeypot.api.app import app
from quantum_honeypot.db.database import init_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def init_test_environment():
    init_db()

def test_healthz_and_readyz():
    res_health = client.get("/healthz")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "HEALTHY"

    res_ready = client.get("/readyz")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "READY"

def test_unauthenticated_protected_endpoint():
    # Attempting to acknowledge alert without token must return 401
    res = client.post("/api/v1/soc/alerts/fake-id/ack")
    assert res.status_code == 401

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
    overview_res = client.get("/api/v1/soc/overview")
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
