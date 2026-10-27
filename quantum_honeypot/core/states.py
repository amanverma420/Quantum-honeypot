"""Quantum state representations: pure statevectors, density matrices, and Bloch coordinates."""

import numpy as np

# Standard Single-Qubit Basis States
KET_0 = np.array([1.0, 0.0], dtype=complex)
KET_1 = np.array([0.0, 1.0], dtype=complex)

# Superposition Basis States
KET_PLUS = (KET_0 + KET_1) / np.sqrt(2)
KET_MINUS = (KET_0 - KET_1) / np.sqrt(2)
KET_PLUS_I = (KET_0 + 1j * KET_1) / np.sqrt(2)
KET_MINUS_I = (KET_0 - 1j * KET_1) / np.sqrt(2)

# Two-Qubit Bell States (Entangled Tripwires)
BELL_PHI_PLUS = (np.kron(KET_0, KET_0) + np.kron(KET_1, KET_1)) / np.sqrt(2)
BELL_PHI_MINUS = (np.kron(KET_0, KET_0) - np.kron(KET_1, KET_1)) / np.sqrt(2)
BELL_PSI_PLUS = (np.kron(KET_0, KET_1) + np.kron(KET_1, KET_0)) / np.sqrt(2)
BELL_PSI_MINUS = (np.kron(KET_0, KET_1) - np.kron(KET_1, KET_0)) / np.sqrt(2)

def to_density_matrix(state: np.ndarray) -> np.ndarray:
    """Convert statevector |psi> to density matrix rho = |psi><psi|."""
    s = np.asarray(state, dtype=complex).reshape(-1, 1)
    return s @ s.conj().T

def bloch_vector(rho: np.ndarray) -> tuple[float, float, float]:
    """Calculate the Bloch sphere vector (rx, ry, rz) from a single-qubit density matrix."""
    rx = float(2 * np.real(rho[0, 1]))
    ry = float(2 * np.imag(rho[1, 0]))
    rz = float(np.real(rho[0, 0] - rho[1, 1]))
    return (rx, ry, rz)

def purity(rho: np.ndarray) -> float:
    """Calculate the purity gamma = Tr(rho^2) of a quantum state."""
    return float(np.real(np.trace(rho @ rho)))

def partial_trace_b(rho_ab: np.ndarray) -> np.ndarray:
    """Trace out subsystem B of a 4x4 bipartite two-qubit density matrix."""
    rho_a = np.zeros((2, 2), dtype=complex)
    for i in range(2):
        for j in range(2):
            rho_a[i, j] = rho_ab[2*i, 2*j] + rho_ab[2*i + 1, 2*j + 1]
    return rho_a
