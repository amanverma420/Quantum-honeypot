"""Quantum Honeytoken Verification and State Collapse Measurement Engine."""

import time
import secrets
import numpy as np
from typing import Dict, Any, List, Optional

from ..core.states import KET_0, KET_1, KET_PLUS, KET_MINUS, to_density_matrix
from ..core.channels import depolarizing_channel, phase_damping_channel
from ..core.fidelity import pure_mixed_fidelity, uhlmann_fidelity_2x2
from ..core.cloning import buzek_hillery_cloner, asymmetric_cloning_attack
from ..core.bell_chsh import calculate_chsh_correlations
from .generator import QuantumHoneytoken

class VerificationResult:
    def __init__(
        self,
        token_id: str,
        strategy: str,
        mean_fidelity: float,
        threshold: float,
        is_intrusion: bool,
        confidence: float,
        chsh_data: Optional[Dict[str, Any]],
        qubit_details: List[Dict[str, Any]],
        source_ip: str = "127.0.0.1",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.token_id = token_id
        self.strategy = strategy
        self.mean_fidelity = mean_fidelity
        self.threshold = threshold
        self.is_intrusion = is_intrusion
        self.confidence = confidence
        self.chsh_data = chsh_data
        self.qubit_details = qubit_details
        self.source_ip = source_ip
        self.metadata = metadata or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_id": self.token_id,
            "strategy": self.strategy,
            "mean_fidelity": round(self.mean_fidelity, 4),
            "threshold": self.threshold,
            "is_intrusion": self.is_intrusion,
            "confidence": round(self.confidence, 4),
            "chsh_result": self.chsh_data,
            "qubit_count": len(self.qubit_details),
            "source_ip": self.source_ip,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

def verify_token_access(
    token: QuantumHoneytoken,
    strategy: str = "legit",
    channel_noise: float = 0.02,
    threshold: float = 0.85,
    source_ip: str = "127.0.0.1",
    user_agent: str = "Internal-Agent/2.0"
) -> VerificationResult:
    """Evaluate physical quantum state fidelity upon token access or interception."""
    qubit_reports: List[Dict[str, Any]] = []
    fidelities: List[float] = []

    for q in token.qubits:
        orig_state = q.state
        prep_basis = q.basis
        
        # Determine observation action per strategy
        if strategy == "legit":
            # Legitimate receiver knows secret preparation basis
            guess_basis = prep_basis
            # Subject only to optical channel depolarizing noise
            noisy_rho = depolarizing_channel(q.density_matrix, channel_noise)
            fid = pure_mixed_fidelity(orig_state, noisy_rho)
            collapsed = False
            
        elif strategy in ("random", "intercept_resend"):
            # Attacker intercepts and guesses basis at random
            guess_basis = secrets.choice(['+', 'x'])
            if guess_basis == prep_basis:
                # Fortuitous basis match
                noisy_rho = depolarizing_channel(q.density_matrix, channel_noise)
                fid = pure_mixed_fidelity(orig_state, noisy_rho)
                collapsed = False
            else:
                # Basis mismatch: wavefunction collapse into orthogonal basis
                # Measurement outcome in wrong basis: 50/50 probability
                outcome = secrets.choice([0, 1])
                if guess_basis == '+':
                    collapsed_state = KET_0 if outcome == 0 else KET_1
                else:
                    collapsed_state = KET_PLUS if outcome == 0 else KET_MINUS
                    
                collapsed_rho = to_density_matrix(collapsed_state)
                noisy_rho = depolarizing_channel(collapsed_rho, channel_noise)
                fid = pure_mixed_fidelity(orig_state, noisy_rho)
                collapsed = True
                
        elif strategy == "fixed_basis":
            # Attacker always measures in rectilinear basis (+)
            guess_basis = '+'
            if prep_basis == '+':
                noisy_rho = depolarizing_channel(q.density_matrix, channel_noise)
                fid = pure_mixed_fidelity(orig_state, noisy_rho)
                collapsed = False
            else:
                outcome = secrets.choice([0, 1])
                collapsed_state = KET_0 if outcome == 0 else KET_1
                collapsed_rho = to_density_matrix(collapsed_state)
                noisy_rho = depolarizing_channel(collapsed_rho, channel_noise)
                fid = pure_mixed_fidelity(orig_state, noisy_rho)
                collapsed = True

        elif strategy == "cloning_uqcm":
            # Attacker applies Universal Quantum Cloning Machine (UQCM)
            guess_basis = "UQCM"
            _, noisy_rho = buzek_hillery_cloner(orig_state)
            noisy_rho = depolarizing_channel(to_density_matrix(orig_state), 0.35 + channel_noise)
            fid = pure_mixed_fidelity(orig_state, noisy_rho)
            collapsed = True

        elif strategy == "asymmetric_clone":
            guess_basis = "Asym-Cloner"
            _, noisy_rho, fid = asymmetric_cloning_attack(orig_state, fidelity_attacker=0.92)
            collapsed = True

        else:
            # Fallback random
            guess_basis = '?'
            fid = 0.50
            collapsed = True

        fidelities.append(fid)
        qubit_reports.append({
            "index": q.index,
            "prep_basis": prep_basis,
            "guess_basis": guess_basis,
            "fidelity": round(fid, 4),
            "state_collapsed": collapsed
        })

    mean_fid = float(np.mean(fidelities))
    
    # Evaluate Entangled Bell pair tripwires if present
    chsh_data = None
    entangled_qubits = [q for q in token.qubits if q.is_entangled]
    if entangled_qubits:
        is_attack = strategy != "legit"
        chsh_data = calculate_chsh_correlations(noise_p=channel_noise, intercepted=is_attack)

    # Intrusion decision
    is_intrusion = mean_fid < threshold or (chsh_data and chsh_data.get("tamper_detected", False))
    
    # Bayesian confidence calculation
    sigma = 0.08
    z_score = abs(threshold - mean_fid) / sigma
    confidence = float(np.clip(1.0 - 0.5 * np.exp(-0.7 * z_score), 0.5, 0.999))

    result = VerificationResult(
        token_id=token.token_id,
        strategy=strategy,
        mean_fidelity=mean_fid,
        threshold=threshold,
        is_intrusion=is_intrusion,
        confidence=confidence,
        chsh_data=chsh_data,
        qubit_details=qubit_reports,
        source_ip=source_ip,
        metadata={"user_agent": user_agent, "target_service": token.target_service}
    )

    # Record event in token history and update status
    token.access_history.append(result.to_dict())
    if is_intrusion:
        token.status = "TRIGGERED"

    return result
