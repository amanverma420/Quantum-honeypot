"""Universal Quantum Cloning Machine (UQCM) and No-Cloning Theorem mechanics."""

import numpy as np
from .gates import I2
from .fidelity import pure_mixed_fidelity

def buzek_hillery_cloner(psi: np.ndarray) -> tuple[np.ndarray, float]:
    """Simulate the Bužek-Hillery optimal state-independent symmetric 1->2 cloner.
    According to the No-Cloning theorem and UQCM bounds:
    rho_copy = (5/6) |psi><psi| + (1/6) |psi_perp><psi_perp|
             = (2/3) |psi><psi| + (1/6) * I
    The theoretical fidelity of each copy is strictly bounded by F = 5/6 ~ 0.8333.
    """
    psi_col = np.asarray(psi, dtype=complex).reshape(-1, 1)
    rho_orig = psi_col @ psi_col.conj().T
    rho_copy = (2.0 / 3.0) * rho_orig + (1.0 / 6.0) * I2
    fidelity = pure_mixed_fidelity(psi, rho_copy)
    return rho_copy, fidelity

def asymmetric_cloning_attack(psi: np.ndarray, fidelity_attacker: float = 0.90) -> tuple[np.ndarray, np.ndarray, float]:
    """Asymmetric 1->2 cloner: Cerf (2000) bound:
    (F_A - 1/2)^2 + (F_B - 1/2)^2 + 2*(F_A - 1/2)*(F_B - 1/2) <= 1/2
    If the attacker attempts to extract a high-fidelity copy for themselves,
    the forwarded state received by the honeypot suffers severe disturbance.
    """
    f_att = np.clip(fidelity_attacker, 0.5, 1.0)
    # Cerf trade-off bound for symmetric/asymmetric cloner
    # In optimal cloner: (F_A - 1/2) and (F_B - 1/2) satisfy the ellipse relation
    # Maximum achievable forwarded fidelity given attacker fidelity:
    x = f_att - 0.5
    # From (x + y)^2 <= 1/2 + 2xy => y = sqrt(1 - 2*x^2) - x ... simplified Cerf bound
    f_fwd = float(np.clip(0.5 + np.sqrt(max(0.0, 0.5 - x**2)) - x * 0.5, 0.35, 0.833))
    
    psi_col = np.asarray(psi, dtype=complex).reshape(-1, 1)
    rho_orig = psi_col @ psi_col.conj().T
    rho_forwarded = (2 * f_fwd - 1) * rho_orig + (1 - f_fwd) * I2
    
    actual_fid = pure_mixed_fidelity(psi, rho_forwarded)
    return rho_orig, rho_forwarded, actual_fid
