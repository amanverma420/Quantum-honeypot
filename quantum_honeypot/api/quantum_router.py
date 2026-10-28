"""Interactive Quantum Research Laboratory API routes."""

import math
from fastapi import APIRouter, HTTPException, Query
from ..schemas.models import (
    SingleQubitStateRequest, QuantumCircuitRequest, BellCHSHRequest,
    BB84SimulationRequest, GroverSearchRequest, NoiseExperimentRequest,
    TeleportationRequest, RepetitionCodeRequest, GroverBenchmarkRequest,
    BellStateRequest
)
from ..core.quantum_lab import QuantumLab
from ..core.advanced_lab import (
    grover_benchmark,
    bell_state_experiment,
    noise_experiment,
    repetition_code_experiment,
    teleportation_experiment,
)

router = APIRouter(prefix="/api/v1/quantum", tags=["Quantum Laboratory"])

@router.post("/bloch")
def get_bloch_state(req: SingleQubitStateRequest):
    """Compute statevector, probabilities, and Bloch sphere coordinates for single qubit."""
    return QuantumLab.single_qubit_bloch(
        theta=req.theta,
        phi=req.phi,
        apply_gate=req.apply_gate
    )

@router.post("/circuit")
def simulate_circuit(req: QuantumCircuitRequest):
    """Simulate an arbitrary multi-qubit circuit (1 to 8 qubits) and return measurement shot counts."""
    return QuantumLab.simulate_circuit(
        n_qubits=req.qubits,
        gate_list=req.gates,
        shots=req.shots,
        seed=req.seed,
    )

@router.post("/bell-chsh")
def run_bell_chsh(req: BellCHSHRequest):
    """Simulate Bell-CHSH inequality test with entangled pairs and compare against classical vs Tsirelson bound."""
    return QuantumLab.bell_chsh_experiment(trials=req.trials)

@router.post("/bb84")
def run_bb84_simulation(req: BB84SimulationRequest):
    """Simulate BB84 Quantum Key Distribution with optional Eve intercept-resend attack and QBER analysis."""
    return QuantumLab.bb84_simulation(
        num_bits=req.num_bits,
        eve_intercept=req.eve_intercept,
        noise_rate=req.noise_rate,
        eve_probability=req.eve_probability,
        qber_threshold=req.qber_threshold,
        seed=req.seed,
    )

@router.post("/grover")
def run_grover_search(req: GroverSearchRequest):
    """Educational demonstration of Grover's quantum search algorithm."""
    return QuantumLab.grover_search(
        num_qubits=req.num_qubits,
        target_state=req.target_state
    )

@router.get("/no-cloning")
def demonstrate_no_cloning(theta: float = Query(1.5707963, ge=0.0, le=3.14159265)):
    """Demonstrate the Bužek-Hillery Universal Quantum Cloning Machine (UQCM) bound."""
    # Optimal universal symmetric 1 -> 2 cloning fidelity is strictly bounded by F = 5/6 ≈ 0.8333
    uqcm_bound = 5.0 / 6.0
    classical_imitation_fidelity = 0.50 + 0.50 * math.cos(theta / 2.0) ** 2
    return {
        "input_state": f"cos({theta/2:.3f})|0> + sin({theta/2:.3f})|1>",
        "uqcm_theoretical_bound": round(uqcm_bound, 4),
        "classical_clone_fidelity": round(classical_imitation_fidelity, 4),
        "perfect_cloning_allowed": False,
        "scientific_statement": (
            "The No-Cloning Theorem (Wootters & Zurek, 1982) proves that arbitrary unknown quantum states "
            "cannot be copied linearly. Optimal universal quantum cloners achieve a maximum fidelity of 5/6 ≈ 0.8333. "
            "Note: This theorem applies to physical quantum states; it does NOT physically prevent attackers "
            "from copying ordinary classical files, passwords, or API keys."
        )
    }

@router.post("/noise")
def run_noise_experiment(req: NoiseExperimentRequest):
    """Apply a validated single-qubit CPTP noise channel and report state metrics."""
    return noise_experiment(req.theta, req.phi, req.channel, req.probability)

@router.post("/repetition-code")
def run_repetition_code(req: RepetitionCodeRequest):
    """Demonstrate the supported single-error correction of a three-qubit repetition code."""
    return repetition_code_experiment(req.code, req.logical_bit, req.error_qubit)

@router.post("/teleportation")
def run_teleportation(req: TeleportationRequest):
    """Execute the Bell-pair, measurement, classical-bit, and correction teleportation circuit."""
    return teleportation_experiment(req.theta, req.phi)

@router.post("/bell-state")
def run_bell_state(req: BellStateRequest):
    """Prepare a Bell pair and report entanglement validation and measurement samples."""
    return bell_state_experiment(req.shots, req.seed)

@router.post("/grover/benchmark")
def run_grover_benchmark(req: GroverBenchmarkRequest):
    """Compare theoretical amplitude amplification with seeded repeated trials."""
    return grover_benchmark(req.num_qubits, req.marked_states, req.trials, req.seed)
