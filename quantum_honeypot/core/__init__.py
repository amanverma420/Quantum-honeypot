"""Core Quantum Mechanics Engine for Quantum Honeypots."""

from .states import (
    KET_0, KET_1, KET_PLUS, KET_MINUS, KET_PLUS_I, KET_MINUS_I,
    BELL_PHI_PLUS, to_density_matrix, bloch_vector, purity, partial_trace_b
)
from .gates import (
    I2, X_GATE, Y_GATE, Z_GATE, H_GATE, S_GATE, CNOT_GATE,
    rx, ry, rz, evolve_density_matrix
)
from .channels import depolarizing_channel, phase_damping_channel, amplitude_damping_channel
from .fidelity import statevector_fidelity, pure_mixed_fidelity, uhlmann_fidelity_2x2, trace_distance
from .cloning import buzek_hillery_cloner, asymmetric_cloning_attack
from .bell_chsh import calculate_chsh_correlations

__all__ = [
    "KET_0", "KET_1", "KET_PLUS", "KET_MINUS", "KET_PLUS_I", "KET_MINUS_I",
    "BELL_PHI_PLUS", "to_density_matrix", "bloch_vector", "purity", "partial_trace_b",
    "I2", "X_GATE", "Y_GATE", "Z_GATE", "H_GATE", "S_GATE", "CNOT_GATE",
    "rx", "ry", "rz", "evolve_density_matrix",
    "depolarizing_channel", "phase_damping_channel", "amplitude_damping_channel",
    "statevector_fidelity", "pure_mixed_fidelity", "uhlmann_fidelity_2x2", "trace_distance",
    "buzek_hillery_cloner", "asymmetric_cloning_attack",
    "calculate_chsh_correlations"
]
