"""Quantum noise channels modeling physical fiber, decoherence, and optical loss."""

import numpy as np
from .gates import I2, X_GATE, Y_GATE, Z_GATE

def depolarizing_channel(rho: np.ndarray, p: float) -> np.ndarray:
    """Apply single-qubit depolarizing channel:
    E(rho) = (1 - p)*rho + (p/3)*(X rho X + Y rho Y + Z rho Z)
    Equivalent to: (1 - 4p/3)*rho + (2p/3)*I
    """
    if p <= 0:
        return rho.copy()
    p = min(1.0, max(0.0, p))
    noise = (
        X_GATE @ rho @ X_GATE.conj().T +
        Y_GATE @ rho @ Y_GATE.conj().T +
        Z_GATE @ rho @ Z_GATE.conj().T
    )
    return (1.0 - p) * rho + (p / 3.0) * noise

def phase_damping_channel(rho: np.ndarray, lambda_param: float) -> np.ndarray:
    """Apply phase damping / dephasing channel (T2 decoherence):
    K0 = [[1, 0], [0, sqrt(1 - lambda)]]
    K1 = [[0, 0], [0, sqrt(lambda)]]
    E(rho) = K0 rho K0^dagger + K1 rho K1^dagger
    """
    if lambda_param <= 0:
        return rho.copy()
    l = min(1.0, max(0.0, lambda_param))
    k0 = np.array([[1.0, 0.0], [0.0, np.sqrt(1.0 - l)]], dtype=complex)
    k1 = np.array([[0.0, 0.0], [0.0, np.sqrt(l)]], dtype=complex)
    return k0 @ rho @ k0.conj().T + k1 @ rho @ k1.conj().T

def amplitude_damping_channel(rho: np.ndarray, gamma: float) -> np.ndarray:
    """Apply amplitude damping channel (T1 energy dissipation to ground state |0>):
    K0 = [[1, 0], [0, sqrt(1 - gamma)]]
    K1 = [[0, sqrt(gamma)], [0, 0]]
    """
    if gamma <= 0:
        return rho.copy()
    g = min(1.0, max(0.0, gamma))
    k0 = np.array([[1.0, 0.0], [0.0, np.sqrt(1.0 - g)]], dtype=complex)
    k1 = np.array([[0.0, np.sqrt(g)], [0.0, 0.0]], dtype=complex)
    return k0 @ rho @ k0.conj().T + k1 @ rho @ k1.conj().T
