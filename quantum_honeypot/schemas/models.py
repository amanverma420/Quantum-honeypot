"""Pydantic schemas for QuantumGuard Honeypot System."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, model_validator

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
    gates: List[Dict[str, Any]] = Field(max_length=256)
    shots: int = Field(ge=10, le=10000, default=1024)
    seed: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_gate_operations(self):
        for item in self.gates:
            gate = item.get("gate")
            if not isinstance(gate, str) or gate.upper() not in {"I", "X", "Y", "Z", "H", "S", "T", "CNOT", "SWAP"}:
                raise ValueError(f"Unsupported gate: {gate}")
            gate = gate.upper()
            if gate in {"I", "X", "Y", "Z", "H", "S", "T"}:
                target = item.get("target")
                if not isinstance(target, int) or isinstance(target, bool) or not 0 <= target < self.qubits:
                    raise ValueError("Single-qubit gate target must be within the circuit")
            elif gate == "CNOT":
                control, target = item.get("control"), item.get("target")
                if (
                    not isinstance(control, int) or isinstance(control, bool)
                    or not isinstance(target, int) or isinstance(target, bool)
                    or not 0 <= control < self.qubits
                    or not 0 <= target < self.qubits
                    or control == target
                ):
                    raise ValueError("CNOT requires distinct control and target qubits in range")
            else:
                q1, q2 = item.get("q1"), item.get("q2")
                if (
                    not isinstance(q1, int) or isinstance(q1, bool)
                    or not isinstance(q2, int) or isinstance(q2, bool)
                    or not 0 <= q1 < self.qubits
                    or not 0 <= q2 < self.qubits
                    or q1 == q2
                ):
                    raise ValueError("SWAP requires distinct q1 and q2 qubits in range")
        return self

class SingleQubitStateRequest(BaseModel):
    theta: float = Field(ge=0.0, le=3.14159265, default=1.5707963)
    phi: float = Field(ge=0.0, le=6.2831853, default=0.0)
    apply_gate: Optional[Literal["I", "X", "Y", "Z", "H", "S", "T"]] = None

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
    num_bits: int = Field(ge=10, le=50000, default=32)
    eve_intercept: bool = False
    noise_rate: float = Field(ge=0.0, le=0.5, default=0.0)
    eve_probability: float = Field(ge=0.0, le=1.0, default=1.0)
    qber_threshold: float = Field(ge=0.0, le=0.5, default=0.11)
    seed: Optional[int] = None

class GroverSearchRequest(BaseModel):
    num_qubits: int = Field(ge=2, le=4, default=3)
    target_state: int = Field(ge=0, default=5)

    @model_validator(mode="after")
    def target_fits_search_space(self):
        if self.target_state >= 2 ** self.num_qubits:
            raise ValueError("target_state must be within the configured search space")
        return self

class NoiseExperimentRequest(BaseModel):
    channel: Literal["bit_flip", "phase_flip", "depolarizing", "amplitude_damping", "phase_damping"]
    probability: float = Field(ge=0.0, le=1.0, default=0.05)
    theta: float = Field(ge=0.0, le=3.141592653589793, default=1.5707963267948966)
    phi: float = Field(ge=0.0, le=6.283185307179586, default=0.0)

class TeleportationRequest(BaseModel):
    theta: float = Field(ge=0.0, le=3.141592653589793, default=1.5707963267948966)
    phi: float = Field(ge=0.0, le=6.283185307179586, default=0.0)

class BellStateRequest(BaseModel):
    shots: int = Field(ge=1, le=10000, default=1024)
    seed: Optional[int] = Field(default=None, ge=0)

class RepetitionCodeRequest(BaseModel):
    code: Literal["bit_flip", "phase_flip"]
    logical_bit: int = Field(ge=0, le=1, default=0)
    error_qubit: int = Field(ge=0, le=2, default=1)

class GroverBenchmarkRequest(BaseModel):
    num_qubits: int = Field(ge=2, le=10, default=3)
    marked_states: List[int] = Field(min_length=1, max_length=1024)
    trials: int = Field(ge=1, le=10000, default=1000)
    seed: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def marked_indices_fit_search_space(self):
        size = 2 ** self.num_qubits
        if len(set(self.marked_states)) != len(self.marked_states):
            raise ValueError("marked_states must not contain duplicates")
        if any(index < 0 or index >= size for index in self.marked_states):
            raise ValueError("marked_states must be within the configured search space")
        return self
