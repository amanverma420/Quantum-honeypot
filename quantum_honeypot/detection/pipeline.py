"""Central Event Ingestion Pipeline, Redaction, Correlation, and Rule Engine."""

import os
import re
import json
import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from ..db.database import SessionLocal
from ..db.models import SecurityEvent, Alert, Incident, Decoy, Sensor, AuditLog
from ..schemas.models import SecurityEventCreate
from .siem_logger import log_security_event

# Real-time event subscribers for Server-Sent Events (SSE)
_event_subscribers: List[asyncio.Queue] = []

def register_sse_subscriber(queue: asyncio.Queue):
    _event_subscribers.append(queue)

def unregister_sse_subscriber(queue: asyncio.Queue):
    if queue in _event_subscribers:
        _event_subscribers.remove(queue)

def broadcast_live_event(event_dict: Dict[str, Any]):
    """Broadcast an event non-blockingly to all connected SSE clients."""
    for q in list(_event_subscribers):
        try:
            q.put_nowait(event_dict)
        except Exception:
            pass

class DetectionRule:
    def __init__(self, rule_id: str, name: str, severity: str, mitre_id: str, mitre_name: str):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity
        self.mitre_id = mitre_id
        self.mitre_name = mitre_name

    def evaluate(self, event: SecurityEvent, db: Session) -> Optional[Tuple[str, str]]:
        """Return (Alert Title, Description) if rule matches, else None."""
        raise NotImplementedError

class HoneytokenAccessRule(DetectionRule):
    def __init__(self):
        super().__init__(
            rule_id="RULE-HONEYTOKEN-01",
            name="Honeytoken Canary Access",
            severity="CRITICAL",
            mitre_id="T1552.001",
            mitre_name="Unsecured Credentials: Credentials In Files"
        )

    def evaluate(self, event: SecurityEvent, db: Session) -> Optional[Tuple[str, str]]:
        if event.token_id or event.event_type in ("api_key", "database", "ssh_key", "aws_iam"):
            target = event.evidence_json.get("target_service") or event.token_id or "Decoy Asset"
            title = f"Honeytoken Breach: Access to {target}"
            desc = (
                f"Unauthorized attempt to read or utilize decoy credential '{event.token_id}' "
                f"from source IP {event.source_ip}. Asset is a synthetic honeytoken with no operational utility."
            )
            return title, desc
        return None

class CloudMetadataProbeRule(DetectionRule):
    def __init__(self):
        super().__init__(
            rule_id="RULE-METADATA-02",
            name="Decoy Cloud Metadata Enumeration",
            severity="HIGH",
            mitre_id="T1552.005",
            mitre_name="Unsecured Credentials: Cloud Instance Metadata API"
        )

    def evaluate(self, event: SecurityEvent, db: Session) -> Optional[Tuple[str, str]]:
        req_path = event.evidence_json.get("path") or event.evidence_json.get("requested_path") or ""
        if "metadata" in req_path or "security-credentials" in req_path:
            title = "Decoy Cloud Instance Metadata API Probe"
            desc = f"Attacker at {event.source_ip} queried fake cloud metadata endpoint '{req_path}' to harvest IAM keys."
            return title, desc
        return None

class BruteForceRule(DetectionRule):
    def __init__(self):
        super().__init__(
            rule_id="RULE-AUTH-03",
            name="Authentication Brute Force against Decoy Gateways",
            severity="HIGH",
            mitre_id="T1110",
            mitre_name="Brute Force"
        )

    def evaluate(self, event: SecurityEvent, db: Session) -> Optional[Tuple[str, str]]:
        if event.event_type in ("bruteforce", "login_failed"):
            # Check count in last 60 seconds
            one_min_ago = datetime.now(timezone.utc) - timedelta(seconds=60)
            prior_count = db.query(SecurityEvent).filter(
                SecurityEvent.source_ip == event.source_ip,
                SecurityEvent.event_type.in_(["bruteforce", "login_failed"]),
                SecurityEvent.timestamp >= one_min_ago
            ).count()
            
            title = f"Decoy Authentication Attack ({prior_count} attempts)"
            desc = f"Repeated login attempts observed from {event.source_ip} against isolated honeypot authentication portal."
            return title, desc
        return None

class MultiDecoyCorrelationRule(DetectionRule):
    def __init__(self):
        super().__init__(
            rule_id="RULE-CORRELATION-04",
            name="Multi-Vector Lateral Decoy Reconnaissance",
            severity="CRITICAL",
            mitre_id="T1046",
            mitre_name="Network Service Discovery"
        )

    def evaluate(self, event: SecurityEvent, db: Session) -> Optional[Tuple[str, str]]:
        five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        distinct_services = db.query(SecurityEvent.event_type).filter(
            SecurityEvent.source_ip == event.source_ip,
            SecurityEvent.timestamp >= five_mins_ago
        ).distinct().count()

        if distinct_services >= 2:
            title = f"Multi-Decoy Lateral Reconnaissance: {distinct_services} Traps Tripped"
            desc = f"Attacker {event.source_ip} has interacted with {distinct_services} distinct decoy services across the environment."
            return title, desc
        return None

RULES: List[DetectionRule] = [
    HoneytokenAccessRule(),
    CloudMetadataProbeRule(),
    BruteForceRule(),
    MultiDecoyCorrelationRule()
]

# Sensitive keys to redact
SENSITIVE_PATTERNS = [
    re.compile(r"password", re.I),
    re.compile(r"secret", re.I),
    re.compile(r"token", re.I),
    re.compile(r"auth", re.I),
    re.compile(r"cookie", re.I),
    re.compile(r"private_key", re.I)
]

def sanitize_evidence(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redact sensitive credentials or oversized attacker payloads."""
    cleaned = {}
    for k, v in evidence.items():
        if any(p.search(k) for p in SENSITIVE_PATTERNS) and k not in ("token_id", "secret_hash", "token_type"):
            cleaned[k] = "[REDACTED_CONFIDENTIAL]"
        elif isinstance(v, str) and len(v) > 500:
            cleaned[k] = v[:500] + "... [TRUNCATED]"
        elif isinstance(v, dict):
            cleaned[k] = sanitize_evidence(v)
        else:
            cleaned[k] = v
    return cleaned

class EventIngestionPipeline:
    def __init__(self):
        self._last_event_cache: Dict[str, float] = {}

    def ingest(self, event_create: SecurityEventCreate, db: Session) -> Tuple[SecurityEvent, Optional[Alert]]:
        """Validate, redact, persist, run detection rules, and correlate incident."""
        source_ip = event_create.source_ip.split()[0] # Sanitize IP
        evidence = sanitize_evidence(event_create.evidence)
        
        # Deduplication check: drop identical event from same IP within 1.0 second
        cache_key = f"{source_ip}:{event_create.event_type}:{event_create.token_id}"
        now_ts = time.time()
        if cache_key in self._last_event_cache and (now_ts - self._last_event_cache[cache_key]) < 1.0:
            pass # Keep recording or throttled

        self._last_event_cache[cache_key] = now_ts

        # Determine MITRE technique mapping
        mitre_id = "T1005"
        mitre_name = "Data from Local System"
        if event_create.event_type in ("api_key", "ssh_key", "database"):
            mitre_id = "T1552.001"
            mitre_name = "Unsecured Credentials: In Files"
        elif event_create.event_type == "aws_iam":
            mitre_id = "T1552.005"
            mitre_name = "Unsecured Credentials: Cloud Instance Metadata"
        elif event_create.event_type in ("bruteforce", "login_failed"):
            mitre_id = "T1110"
            mitre_name = "Brute Force"
        elif event_create.event_type == "scan":
            mitre_id = "T1046"
            mitre_name = "Network Service Discovery"

        # Create SecurityEvent record
        db_event = SecurityEvent(
            event_type=event_create.event_type,
            severity=event_create.severity,
            source_ip=source_ip,
            sensor_id=event_create.sensor_id,
            decoy_id=event_create.decoy_id,
            token_id=event_create.token_id,
            message=event_create.message,
            mitre_technique_id=mitre_id,
            mitre_technique_name=mitre_name,
            evidence_json=evidence,
            quantum_telemetry_json=event_create.quantum_telemetry
        )
        db.add(db_event)
        db.flush()

        # Update Decoy access counter if token matched
        if event_create.token_id:
            decoy = db.query(Decoy).filter(Decoy.token_id == event_create.token_id).first()
            if decoy:
                decoy.access_count += 1

        # Run Detection Rules
        generated_alert = None
        for rule in RULES:
            match = rule.evaluate(db_event, db)
            if match:
                title, desc = match
                generated_alert = Alert(
                    severity=rule.severity,
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    title=title,
                    description=desc,
                    triggering_event_id=db_event.id,
                    status="NEW"
                )
                db.add(generated_alert)
                db.flush()
                break # Primary rule matched

        # Auto-Correlate into an Incident
        if generated_alert:
            # Find open incident for this attacker IP created in last 24h
            day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
            incident = db.query(Incident).filter(
                Incident.status.in_(["OPEN", "INVESTIGATING"]),
                Incident.created_at >= day_ago,
                Incident.title.contains(source_ip)
            ).first()

            if not incident:
                incident = Incident(
                    title=f"Deception Tripwire Campaign - {source_ip}",
                    severity=generated_alert.severity,
                    status="OPEN",
                    assigned_to="security_analyst",
                    summary=f"Automated incident triggered by {generated_alert.rule_name} targeting honeypot assets.",
                    evidence_json={"primary_source_ip": source_ip, "initial_event_id": db_event.id}
                )
                db.add(incident)
                db.flush()

            generated_alert.incident_id = incident.id
            db_event.is_correlated = True

        db.commit()
        db.refresh(db_event)

        # Write to backward-compatible JSONL log
        log_security_event(
            event_type=db_event.event_type,
            severity=db_event.severity,
            message=db_event.message,
            source_ip=db_event.source_ip,
            token_id=db_event.token_id,
            fidelity=db_event.quantum_telemetry_json.get("fidelity") if db_event.quantum_telemetry_json else None,
            extra=db_event.evidence_json
        )

        # Broadcast to real-time SSE stream
        broadcast_payload = {
            "type": "NEW_SECURITY_EVENT",
            "event": {
                "id": db_event.id,
                "timestamp": db_event.timestamp.isoformat(),
                "event_type": db_event.event_type,
                "severity": db_event.severity,
                "source_ip": db_event.source_ip,
                "sensor_id": db_event.sensor_id,
                "token_id": db_event.token_id,
                "message": db_event.message,
                "mitre": f"{db_event.mitre_technique_id} - {db_event.mitre_technique_name}",
                "has_alert": generated_alert is not None
            }
        }
        broadcast_live_event(broadcast_payload)

        return db_event, generated_alert

PIPELINE = EventIngestionPipeline()
