"""SQLAlchemy ORM models for QuantumGuard persistent database."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), default="analyst", nullable=False)  # admin, analyst, viewer
    created_at = Column(DateTime, default=get_utc_now)
    is_active = Column(Boolean, default=True)

class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    sensor_type = Column(String(64), nullable=False)  # http_gateway, ssh_bastion, canary_fs
    host = Column(String(128), default="127.0.0.1")
    port = Column(Integer, default=0)
    status = Column(String(32), default="ACTIVE")
    last_heartbeat = Column(DateTime, default=get_utc_now)

class Decoy(Base):
    __tablename__ = "decoys"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    decoy_type = Column(String(64), nullable=False)  # api_key, database, aws_iam, ssh_key, canary_file
    target_service = Column(String(128), nullable=False)
    token_id = Column(String(64), index=True, nullable=False)
    secret_hash = Column(String(128), nullable=False)  # SHA-256 hash of secret, never cleartext
    status = Column(String(32), default="ARMED")
    created_at = Column(DateTime, default=get_utc_now)
    access_count = Column(Integer, default=0)

class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=get_utc_now, index=True)
    event_type = Column(String(64), index=True, nullable=False)
    severity = Column(String(32), index=True, default="INFO")
    source_ip = Column(String(64), index=True, nullable=False)
    sensor_id = Column(String(64), default="gateway-default")
    decoy_id = Column(String(64), nullable=True)
    token_id = Column(String(64), index=True, nullable=True)
    message = Column(Text, nullable=False)
    mitre_technique_id = Column(String(32), default="T1005")
    mitre_technique_name = Column(String(128), default="Data from Local System")
    evidence_json = Column(JSON, default=dict)
    quantum_telemetry_json = Column(JSON, nullable=True)
    is_correlated = Column(Boolean, default=False)

    alerts = relationship("Alert", back_populates="triggering_event")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=get_utc_now, index=True)
    severity = Column(String(32), index=True, default="HIGH")
    rule_id = Column(String(64), index=True, nullable=False)
    rule_name = Column(String(128), nullable=False)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    triggering_event_id = Column(String(36), ForeignKey("security_events.id"), nullable=False)
    status = Column(String(32), default="NEW", index=True)  # NEW, ACKNOWLEDGED, RESOLVED, CLOSED
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=True)

    triggering_event = relationship("SecurityEvent", back_populates="alerts")
    incident = relationship("Incident", back_populates="alerts")

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=get_utc_now, index=True)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)
    title = Column(String(256), nullable=False)
    severity = Column(String(32), default="HIGH", index=True)
    status = Column(String(32), default="OPEN", index=True)  # OPEN, INVESTIGATING, RESOLVED, CLOSED
    assigned_to = Column(String(64), default="security_analyst")
    summary = Column(Text, nullable=False)
    evidence_json = Column(JSON, default=dict)

    alerts = relationship("Alert", back_populates="incident")
    notes = relationship("AnalystNote", back_populates="incident", cascade="all, delete-orphan")

class AnalystNote(Base):
    __tablename__ = "analyst_notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    author_username = Column(String(64), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)

    incident = relationship("Incident", back_populates="notes")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=get_utc_now, index=True)
    actor_username = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)
    details_json = Column(JSON, default=dict)

class QuantumExperimentRecord(Base):
    __tablename__ = "quantum_experiments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=get_utc_now)
    experiment_type = Column(String(64), nullable=False)
    qubits = Column(Integer, default=1)
    params_json = Column(JSON, default=dict)
    results_json = Column(JSON, default=dict)
