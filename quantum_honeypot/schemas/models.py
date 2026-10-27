"""Pydantic schemas for QuantumGuard Honeypot System."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class TokenBase(BaseModel):
    token_id: str
    token_type: str
    target_service: str
    status: str = "ARMED"
    created_at: str

class SecurityEventCreate(BaseModel):
    event_type: str
    severity: str = "INFO"
    message: str
    source_ip: str
    sensor_id: str = "gateway-default"
    decoy_id: Optional[str] = None
    token_id: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    quantum_telemetry: Optional[Dict[str, Any]] = None

class SecurityEventResponse(BaseModel):
    id: str
    timestamp: str
    event_type: str
    severity: str
    message: str
    source_ip: str
    sensor_id: str
    decoy_id: Optional[str]
    token_id: Optional[str]
    mitre_technique_id: str
    mitre_technique_name: str
    evidence: Dict[str, Any]
    quantum_telemetry: Optional[Dict[str, Any]]
    is_correlated: bool = False

class AlertResponse(BaseModel):
    id: str
    created_at: str
    severity: str
    rule_id: str
    rule_name: str
    title: str
    description: str
    triggering_event_id: str
    status: str = "NEW"  # NEW, ACKNOWLEDGED, RESOLVED

class IncidentCreate(BaseModel):
    title: str
    severity: str = "HIGH"
    summary: str
    assigned_to: Optional[str] = "analyst"

class IncidentStatusUpdate(BaseModel):
    status: str  # OPEN, INVESTIGATING, RESOLVED, CLOSED
    resolution_note: Optional[str] = None

class AnalystNoteCreate(BaseModel):
    content: str

class AnalystNoteResponse(BaseModel):
    id: str
    incident_id: str
    author_username: str
    content: str
    created_at: str

class IncidentResponse(BaseModel):
    id: str
    created_at: str
    updated_at: str
    title: str
    severity: str
    status: str
    assigned_to: Optional[str]
    summary: str
    event_count: int = 0
    notes: List[AnalystNoteResponse] = Field(default_factory=list)

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    created_at: str

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class DecoyCreate(BaseModel):
    name: str
    decoy_type: str
    target_service: str
    description: Optional[str] = None

class DecoyResponse(BaseModel):
    id: str
    name: str
    decoy_type: str
    target_service: str
    token_id: str
    status: str
    created_at: str
    access_count: int = 0

class SOCStatsResponse(BaseModel):
    total_events: int
    critical_alerts: int
    open_incidents: int
    active_decoys: int
    events_last_24h: int
    severity_breakdown: Dict[str, int]
    mitre_breakdown: Dict[str, int]
    system_health: str = "OPERATIONAL"

# Quantum API Schemas
class QuantumCircuitRequest(BaseModel):
    qubits: int = Field(ge=1, le=8, default=2)
    gates: List[Dict[str, Any]]  # e.g. [{"gate": "H", "target": 0}, {"gate": "CNOT", "control": 0, "target": 1}]
    shots: int = Field(ge=10, le=10000, default=1024)

class SingleQubitStateRequest(BaseModel):
    theta: float = Field(ge=0.0, le=3.14159265, default=1.5707963)
    phi: float = Field(ge=0.0, le=6.2831853, default=0.0)
    apply_gate: Optional[str] = None  # X, Y, Z, H, S, T

class NoiseChannelRequest(BaseModel):
    channel_type: str  # depolarizing, bit_flip, phase_flip, amplitude_damping
    noise_param: float = Field(ge=0.0, le=1.0, default=0.05)
    initial_state: str = "zero"  # zero, one, plus, minus

class BellCHSHRequest(BaseModel):
    trials: int = Field(ge=100, le=10000, default=1000)
    theta_a1: float = 0.0
    theta_a2: float = 1.5707963267948966  # pi/2
    theta_b1: float = 0.7853981633974483  # pi/4
    theta_b2: float = 2.356194490192345  # 3*pi/4

class BB84SimulationRequest(BaseModel):
    num_bits: int = Field(ge=10, le=256, default=32)
    eve_intercept: bool = False
    noise_rate: float = Field(ge=0.0, le=0.5, default=0.0)

class GroverSearchRequest(BaseModel):
    num_qubits: int = Field(ge=2, le=4, default=3)
    target_state: int = Field(ge=0, default=5)
