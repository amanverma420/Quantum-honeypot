"""SOC Management, Real-time Telemetry, Incidents, and SSE Streaming API."""

import io
import csv
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..db.database import get_db
from ..db.models import SecurityEvent, Alert, Incident, AnalystNote, Decoy, Sensor, AuditLog, User
from ..schemas.models import (
    SecurityEventResponse, AlertResponse, IncidentResponse, IncidentCreate,
    IncidentStatusUpdate, AnalystNoteCreate, AnalystNoteResponse, DecoyResponse,
    SOCStatsResponse, SecurityEventCreate
)
from ..security.auth import get_current_user, require_analyst, require_viewer, require_admin
from ..detection.pipeline import PIPELINE, register_sse_subscriber, unregister_sse_subscriber

router = APIRouter(prefix="/api/v1/soc", tags=["SOC Dashboard & Telemetry"])

@router.get("/overview", response_model=SOCStatsResponse)
def get_soc_overview(db: Session = Depends(get_db)):
    """Retrieve operational metrics and real-time statistics backed by database records."""
    total_events = db.query(SecurityEvent).count()
    critical_alerts = db.query(Alert).filter(Alert.severity.in_(["CRITICAL", "HIGH"])).count()
    open_incidents = db.query(Incident).filter(Incident.status.in_(["OPEN", "INVESTIGATING"])).count()
    active_decoys = db.query(Decoy).filter(Decoy.status == "ARMED").count()

    one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    events_last_24h = db.query(SecurityEvent).filter(SecurityEvent.timestamp >= one_day_ago).count()

    # Severity distribution
    sev_rows = db.query(SecurityEvent.severity, func.count(SecurityEvent.id)).group_by(SecurityEvent.severity).all()
    sev_dict = {s: c for s, c in sev_rows}

    # MITRE breakdown
    mitre_rows = db.query(SecurityEvent.mitre_technique_id, func.count(SecurityEvent.id)).group_by(SecurityEvent.mitre_technique_id).all()
    mitre_dict = {m: c for m, c in mitre_rows}

    return {
        "total_events": total_events,
        "critical_alerts": critical_alerts,
        "open_incidents": open_incidents,
        "active_decoys": active_decoys,
        "events_last_24h": events_last_24h,
        "severity_breakdown": sev_dict,
        "mitre_breakdown": mitre_dict,
        "system_health": "OPERATIONAL"
    }

@router.get("/events")
def list_security_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    source_ip: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve paginated, filtered security events with sanitized metadata."""
    query = db.query(SecurityEvent)
    if severity:
        query = query.filter(SecurityEvent.severity == severity.upper())
    if event_type:
        query = query.filter(SecurityEvent.event_type == event_type)
    if source_ip:
        query = query.filter(SecurityEvent.source_ip.contains(source_ip))
    if search:
        query = query.filter(
            (SecurityEvent.message.contains(search)) |
            (SecurityEvent.token_id.contains(search)) |
            (SecurityEvent.source_ip.contains(search))
        )

    total = query.count()
    events = query.order_by(desc(SecurityEvent.timestamp)).offset(offset).limit(limit).all()

    items = []
    for e in events:
        items.append({
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "event_type": e.event_type,
            "severity": e.severity,
            "message": e.message,
            "source_ip": e.source_ip,
            "sensor_id": e.sensor_id,
            "decoy_id": e.decoy_id,
            "token_id": e.token_id,
            "mitre_technique_id": e.mitre_technique_id,
            "mitre_technique_name": e.mitre_technique_name,
            "evidence": e.evidence_json or {},
            "quantum_telemetry": e.quantum_telemetry_json,
            "is_correlated": e.is_correlated
        })

    return {"total": total, "limit": limit, "offset": offset, "events": items}

@router.get("/alerts")
def list_alerts(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List detection alerts and trigger status."""
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status.upper())
    alerts = query.order_by(desc(Alert.created_at)).limit(limit).all()
    
    return [
        {
            "id": a.id,
            "created_at": a.created_at.isoformat(),
            "severity": a.severity,
            "rule_id": a.rule_id,
            "rule_name": a.rule_name,
            "title": a.title,
            "description": a.description,
            "triggering_event_id": a.triggering_event_id,
            "status": a.status,
            "incident_id": a.incident_id
        }
        for a in alerts
    ]

@router.post("/alerts/{alert_id}/ack")
def acknowledge_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst)
):
    """Acknowledge an active security alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "ACKNOWLEDGED"
    db.commit()
    return {"status": "SUCCESS", "alert_id": alert_id, "new_status": "ACKNOWLEDGED"}

@router.get("/incidents")
def list_incidents(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List active and resolved incidents with analyst notes."""
    query = db.query(Incident)
    if status:
        query = query.filter(Incident.status == status.upper())
    incidents = query.order_by(desc(Incident.created_at)).limit(limit).all()

    res = []
    for inc in incidents:
        notes = [
            {
                "id": n.id,
                "incident_id": n.incident_id,
                "author_username": n.author_username,
                "content": n.content,
                "created_at": n.created_at.isoformat()
            }
            for n in inc.notes
        ]
        res.append({
            "id": inc.id,
            "created_at": inc.created_at.isoformat(),
            "updated_at": inc.updated_at.isoformat(),
            "title": inc.title,
            "severity": inc.severity,
            "status": inc.status,
            "assigned_to": inc.assigned_to,
            "summary": inc.summary,
            "event_count": len(inc.alerts),
            "notes": notes
        })
    return res

@router.patch("/incidents/{incident_id}/status")
def update_incident_status(
    incident_id: str,
    update: IncidentStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst)
):
    """Update incident status (OPEN, INVESTIGATING, RESOLVED, CLOSED) and log analyst note."""
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    old_status = inc.status
    inc.status = update.status.upper()
    
    if update.resolution_note:
        note = AnalystNote(
            incident_id=inc.id,
            author_username=user.username,
            content=f"[Status Change {old_status} -> {inc.status}] {update.resolution_note}"
        )
        db.add(note)

    # Record Audit Log
    db.add(AuditLog(
        actor_username=user.username,
        action="UPDATE_INCIDENT_STATUS",
        entity_type="incident",
        entity_id=inc.id,
        details_json={"from": old_status, "to": inc.status}
    ))
    db.commit()
    return {"status": "SUCCESS", "incident_id": inc.id, "new_status": inc.status}

@router.post("/incidents/{incident_id}/notes")
def add_analyst_note(
    incident_id: str,
    note_create: AnalystNoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst)
):
    """Add a timestamped analyst investigation note to an incident."""
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    note = AnalystNote(
        incident_id=inc.id,
        author_username=user.username,
        content=note_create.content
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return {
        "id": note.id,
        "incident_id": note.incident_id,
        "author_username": note.author_username,
        "content": note.content,
        "created_at": note.created_at.isoformat()
    }

@router.get("/decoys")
def list_decoys(db: Session = Depends(get_db)):
    """List registered deception honeytokens and canary sensors."""
    decoys = db.query(Decoy).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "decoy_type": d.decoy_type,
            "target_service": d.target_service,
            "token_id": d.token_id,
            "status": d.status,
            "created_at": d.created_at.isoformat(),
            "access_count": d.access_count
        }
        for d in decoys
    ]

@router.post("/decoys/simulate-breach")
def simulate_decoy_breach(
    token_id: str = Query("qtok_stripe_live_prod"),
    source_ip: str = Query("192.168.1.105"),
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst)
):
    """Interactive endpoint to trigger an authorized synthetic test event for verification."""
    decoy = db.query(Decoy).filter(Decoy.token_id == token_id).first()
    service = decoy.target_service if decoy else "Simulated Decoy Gateway"
    
    event_create = SecurityEventCreate(
        event_type=decoy.decoy_type if decoy else "api_key",
        severity="CRITICAL",
        message=f"Manual operator verification breach triggered against '{service}' from {source_ip}.",
        source_ip=source_ip,
        sensor_id="manual-test-harness",
        token_id=token_id,
        evidence={"authorized_drill": True, "operator": user.username, "target_service": service},
        quantum_telemetry={"fidelity": 0.5211, "threshold": 0.85, "is_attack": True}
    )
    db_event, alert = PIPELINE.ingest(event_create, db)
    return {
        "status": "SUCCESS",
        "event_id": db_event.id,
        "alert_generated": alert.title if alert else None,
        "incident_id": alert.incident_id if alert else None
    }

@router.get("/reports/export")
def export_security_report(
    format: str = Query("csv", pattern="^(csv|json)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_viewer)
):
    """Export sanitized security events and incidents in CSV or JSON format."""
    events = db.query(SecurityEvent).order_by(desc(SecurityEvent.timestamp)).limit(500).all()
    
    if format == "json":
        data = [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "severity": e.severity,
                "source_ip": e.source_ip,
                "token_id": e.token_id,
                "mitre": f"{e.mitre_technique_id} - {e.mitre_technique_name}",
                "message": e.message
            }
            for e in events
        ]
        return data

    # CSV Export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp (UTC)", "Event Type", "Severity", "Source IP", "Token ID", "MITRE Technique", "Message"])
    for e in events:
        writer.writerow([
            e.id,
            e.timestamp.isoformat(),
            e.event_type,
            e.severity,
            e.source_ip,
            e.token_id or "",
            f"{e.mitre_technique_id} - {e.mitre_technique_name}",
            e.message
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=quantumguard_security_export.csv"}
    )

@router.get("/stream")
async def sse_event_stream():
    """Server-Sent Events (SSE) endpoint broadcasting live security events to the dashboard."""
    queue = asyncio.Queue(maxsize=100)
    register_sse_subscriber(queue)

    async def event_generator():
        try:
            # Send initial connection handshake
            yield f"data: {json.dumps({'type': 'CONNECTED', 'message': 'QuantumGuard Real-time Stream Active'})}\n\n"
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat comment to keep connection alive through firewalls/proxies
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            unregister_sse_subscriber(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
