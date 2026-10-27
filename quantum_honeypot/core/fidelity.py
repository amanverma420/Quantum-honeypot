"""Quantum state fidelity and distance metrics (Uhlmann fidelity, Trace distance)."""

import numpy as np

def statevector_fidelity(psi: np.ndarray, phi: np.ndarray) -> float:
    """Compute state fidelity between two pure statevectors |psi> and |phi>:
    F = |<psi|phi>|^2
    """
    p1 = psi.ravel()
    p2 = phi.ravel()
    overlap = np.vdot(p1, p2)
    return float(np.abs(overlap) ** 2)

def pure_mixed_fidelity(psi: np.ndarray, rho: np.ndarray) -> float:
    """Compute fidelity between pure state |psi> and density matrix rho:
    F = <psi| rho |psi>
    """
    p = psi.ravel()
    res = np.vdot(p, rho @ p)
    return float(np.clip(np.real(res), 0.0, 1.0))

def uhlmann_fidelity_2x2(rho: np.ndarray, sigma: np.ndarray) -> float:
    """Exact Uhlmann fidelity for single-qubit 2x2 density matrices:
    F(rho, sigma) = Tr(rho * sigma) + 2 * sqrt(det(rho) * det(sigma))
    """
    tr_prod = np.real(np.trace(rho @ sigma))
    det_rho = max(0.0, float(np.real(np.linalg.det(rho))))
    det_sigma = max(0.0, float(np.real(np.linalg.det(sigma))))
    f = tr_prod + 2.0 * np.sqrt(det_rho * det_sigma)
    return float(np.clip(f, 0.0, 1.0))

def trace_distance(rho: np.ndarray, sigma: np.ndarray) -> float:
    """Compute trace distance D(rho, sigma) = 0.5 * Tr|rho - sigma|."""
    diff = rho - sigma
    eigenvalues = np.linalg.eigvalsh(diff)
    return float(0.5 * np.sum(np.abs(eigenvalues)))
