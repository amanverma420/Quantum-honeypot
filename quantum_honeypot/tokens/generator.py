"""Quantum Honeytoken generation with embedded qubit tripwire registers."""

import os
import time
import secrets
import hashlib
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from ..core.states import KET_0, KET_1, KET_PLUS, KET_MINUS, to_density_matrix
from ..core.gates import H_GATE, X_GATE

@dataclass
class QubitTripwire:
    index: int
    bit: int                  # 0 or 1
    basis: str                # '+' (rectilinear Z) or 'x' (diagonal X)
    state: np.ndarray         # Statevector |psi>
    density_matrix: np.ndarray # rho = |psi><psi|
    is_entangled: bool = False
    bell_pair_id: Optional[str] = None

@dataclass
class QuantumHoneytoken:
    token_id: str
    token_type: str           # 'api_key', 'aws_iam', 'database', 'jwt', 'ssh_key'
    decoy_secret: str         # The string credential given to bait attackers
    target_service: str       # E.g. "PostgreSQL Prod Decoy", "Stripe API Key", "AWS S3 Master"
    n_tripwires: int
    qubits: List[QubitTripwire]
    created_at: float = field(default_factory=time.time)
    status: str = "ARMED"     # "ARMED", "TRIGGERED", "REVOKED"
    access_history: List[Dict[str, Any]] = field(default_factory=list)

def generate_honeytoken(
    token_type: str = "api_key",
    target_service: str = "Internal Cloud Gateway",
    n_qubits: int = 8,
    enable_entanglement: bool = True
) -> QuantumHoneytoken:
    """Generate a high-entropy decoy credential bound to a quantum tripwire register."""
    token_id = f"qtok_{secrets.token_hex(8)}"
    
    # Generate realistic decoy secret formats
    if token_type == "api_key":
        decoy_secret = f"qg_live_{secrets.token_urlsafe(32)}"
    elif token_type == "aws_iam":
        decoy_secret = f"AKIA{secrets.token_hex(8).upper()}:{secrets.token_urlsafe(30)}"
    elif token_type == "database":
        decoy_secret = f"postgresql://db_admin:{secrets.token_urlsafe(16)}@decoy-db.quantumguard.internal:5432/production"
    elif token_type == "jwt":
        header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        payload = secrets.token_urlsafe(24)
        sig = secrets.token_urlsafe(16)
        decoy_secret = f"{header}.{payload}.{sig}"
    elif token_type == "ssh_key":
        decoy_secret = f"-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn\n{secrets.token_hex(48)}\n-----END OPENSSH PRIVATE KEY-----"
    else:
        decoy_secret = f"SECRET_{secrets.token_hex(16)}"

    qubits: List[QubitTripwire] = []
    for i in range(n_qubits):
        bit = secrets.randbelow(2)
        basis = secrets.choice(['+', 'x'])
        
        # State preparation
        if basis == '+':
            # Rectilinear basis: |0> or |1>
            state = KET_0.copy() if bit == 0 else KET_1.copy()
        else:
            # Diagonal basis: |+> or |->
            state = KET_PLUS.copy() if bit == 0 else KET_MINUS.copy()
            
        rho = to_density_matrix(state)
        entangled = enable_entanglement and (i % 2 == 0)
        bell_id = f"bell_{token_id}_{i}" if entangled else None
        
        qubits.append(QubitTripwire(
            index=i,
            bit=bit,
            basis=basis,
            state=state,
            density_matrix=rho,
            is_entangled=entangled,
            bell_pair_id=bell_id
        ))

    return QuantumHoneytoken(
        token_id=token_id,
        token_type=token_type,
        decoy_secret=decoy_secret,
        target_service=target_service,
        n_tripwires=n_qubits,
        qubits=qubits
    )
