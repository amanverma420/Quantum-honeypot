"""Quantum gates, unitary operators, and measurement projectors."""

import numpy as np

# Single-Qubit Standard Operators
I2 = np.eye(2, dtype=complex)
X_GATE = np.array([[0, 1], [1, 0]], dtype=complex)
Y_GATE = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z_GATE = np.array([[1, 0], [0, -1]], dtype=complex)
H_GATE = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
S_GATE = np.array([[1, 0], [0, 1j]], dtype=complex)

# Two-Qubit Operators
CNOT_GATE = np.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 0, 1],
    [0, 0, 1, 0]
], dtype=complex)

# Projective Measurement Operators
P_0 = np.array([[1, 0], [0, 0]], dtype=complex)
P_1 = np.array([[0, 0], [0, 1]], dtype=complex)
P_PLUS = 0.5 * np.array([[1, 1], [1, 1]], dtype=complex)
P_MINUS = 0.5 * np.array([[1, -1], [-1, 1]], dtype=complex)

def rx(theta: float) -> np.ndarray:
    """Single-qubit rotation around X-axis by angle theta."""
    return np.array([
        [np.cos(theta / 2), -1j * np.sin(theta / 2)],
        [-1j * np.sin(theta / 2), np.cos(theta / 2)]
    ], dtype=complex)

def ry(theta: float) -> np.ndarray:
    """Single-qubit rotation around Y-axis by angle theta."""
    return np.array([
        [np.cos(theta / 2), -np.sin(theta / 2)],
        [np.sin(theta / 2), np.cos(theta / 2)]
    ], dtype=complex)

def rz(theta: float) -> np.ndarray:
    """Single-qubit rotation around Z-axis by angle theta."""
    return np.array([
        [np.exp(-1j * theta / 2), 0],
        [0, np.exp(1j * theta / 2)]
    ], dtype=complex)

def evolve_density_matrix(rho: np.ndarray, unitary: np.ndarray) -> np.ndarray:
    """Apply unitary transformation U to density matrix rho: rho' = U rho U^dagger."""
    return unitary @ rho @ unitary.conj().T
