"""Unit tests for Event Ingestion Pipeline, redaction, and detection rules."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from quantum_honeypot.db.models import Base, SecurityEvent, Alert, Incident, Decoy
from quantum_honeypot.schemas.models import SecurityEventCreate
from quantum_honeypot.detection.pipeline import PIPELINE, sanitize_evidence

# Setup isolated in-memory test database
test_engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    with TestingSessionLocal() as db:
        db.add(Decoy(
            id="decoy-test",
            name="Test Stripe Decoy",
            decoy_type="api_key",
            target_service="Stripe",
            token_id="qtok_stripe_test",
            secret_hash="fakehash",
            status="ARMED"
        ))
        db.commit()
    yield
    Base.metadata.drop_all(bind=test_engine)

def test_evidence_sanitization_redacts_secrets():
    raw_evidence = {
        "user_agent": "curl/7.68.0",
        "password": "CleartextPassword!",
        "client_secret": "sk_live_secret123",
        "auth_cookie": "sess=xyz",
        "safe_field": "public_data"
    }
    sanitized = sanitize_evidence(raw_evidence)
    assert sanitized["password"] == "[REDACTED_CONFIDENTIAL]"
    assert sanitized["client_secret"] == "[REDACTED_CONFIDENTIAL]"
    assert sanitized["auth_cookie"] == "[REDACTED_CONFIDENTIAL]"
    assert sanitized["safe_field"] == "public_data"

def test_pipeline_ingest_honeytoken_breach():
    with TestingSessionLocal() as db:
        event_create = SecurityEventCreate(
            event_type="api_key",
            severity="CRITICAL",
            message="Attacker touched canary key",
            source_ip="198.51.100.42",
            token_id="qtok_stripe_test",
            evidence={"user_password": "supersecretpassword", "target_service": "Stripe Gateway"}
        )
        db_event, alert = PIPELINE.ingest(event_create, db)

        assert db_event.id is not None
        assert db_event.evidence_json["user_password"] == "[REDACTED_CONFIDENTIAL]"
        assert alert is not None
        assert alert.rule_id == "RULE-HONEYTOKEN-01"
        assert alert.severity == "CRITICAL"
        assert alert.incident_id is not None

        # Verify incident was created and correlated
        incident = db.query(Incident).filter(Incident.id == alert.incident_id).first()
        assert incident is not None
        assert "198.51.100.42" in incident.title

        duplicate, duplicate_alert = PIPELINE.ingest(event_create, db)
        assert duplicate.id == db_event.id
        assert duplicate_alert.id == alert.id
        assert db.query(SecurityEvent).count() == 1
