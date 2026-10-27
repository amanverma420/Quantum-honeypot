"""Entanglement Canary Tripwire using Clauser-Horne-Shimony-Holt (CHSH) Bell inequality."""

import numpy as np

def calculate_chsh_correlations(noise_p: float = 0.0, intercepted: bool = False, n_shots: int = 1000) -> dict:
    """Evaluate CHSH parameter S for an entangled Bell pair canary (|Phi+>).
    Angles:
      Alice: a0 = 0, a1 = pi/4 (45 deg)
      Bob:   b0 = pi/8 (22.5 deg), b1 = -pi/8 (-22.5 deg)
    
    Quantum prediction for pure Bell state:
      E(a0, b0) = cos(2 * (0 - pi/8)) = cos(-pi/4) = 1/sqrt(2) ~ 0.7071
      E(a0, b1) = cos(2 * (0 - (-pi/8))) = cos(pi/4) = 1/sqrt(2) ~ 0.7071
      E(a1, b0) = cos(2 * (pi/4 - pi/8)) = cos(pi/4) = 1/sqrt(2) ~ 0.7071
      E(a1, b1) = cos(2 * (pi/4 - (-pi/8))) = cos(3*pi/4) = -1/sqrt(2) ~ -0.7071
      S = E(a0, b0) + E(a0, b1) + E(a1, b0) - E(a1, b1) = 4 / sqrt(2) = 2 * sqrt(2) ~ 2.8284 (Tsirelson bound)
      
    If intercepted/measured classically (local realism):
      |S| <= 2.0 (Bell Inequality)
    """
    angles_a = [0.0, np.pi / 4]
    angles_b = [np.pi / 8, -np.pi / 8]
    
    e_vals = {}
    for i, a in enumerate(angles_a):
        for j, b in enumerate(angles_b):
            if intercepted:
                # Intercept-resend collapses entanglement to classical mixture -> max S <= sqrt(2) or 2.0
                e_theory = 0.5 * np.cos(2 * (a - b))
            else:
                # Intact quantum channel with depolarizing noise
                e_theory = (1.0 - 1.333 * noise_p) * np.cos(2 * (a - b))
            
            # Add statistical sampling variance
            std = np.sqrt(max(0.001, (1.0 - e_theory**2) / n_shots))
            sampled = float(np.clip(np.random.normal(e_theory, std), -1.0, 1.0))
            e_vals[f"E_a{i}_b{j}"] = sampled

    s_val = e_vals["E_a0_b0"] + e_vals["E_a0_b1"] + e_vals["E_a1_b0"] - e_vals["E_a1_b1"]
    violated = s_val > 2.0
    
    return {
        "S": float(s_val),
        "classical_bound": 2.0,
        "quantum_bound": float(2.0 * np.sqrt(2.0)),
        "is_entangled": bool(violated),
        "tamper_detected": bool(not violated),
        "correlations": e_vals
    }
