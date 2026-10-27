"""Adaptive Bayesian Intrusion Detector and Dynamic Thresholding Engine."""

import numpy as np
from typing import Dict, Any

class BayesianQuantumDetector:
    def __init__(
        self,
        base_noise: float = 0.02,
        prior_attack_prob: float = 0.05,
        target_false_positive_rate: float = 0.005
    ):
        self.base_noise = base_noise
        self.prior_attack = prior_attack_prob
        self.target_fpr = target_false_positive_rate

    def calculate_dynamic_threshold(self, observed_noise_floor: float = 0.02) -> float:
        """Dynamically compute optimal fidelity threshold tau.
        Under legitimate access: F_legit ~ Normal(mu_legit, sigma_legit^2)
        mu_legit = 1 - (2/3)*noise
        sigma_legit = sqrt(noise / (4 * n_qubits)) ~ 0.04
        To enforce P(F < tau | Legit) <= target_fpr:
        tau = mu_legit - z_{1 - fpr} * sigma_legit
        """
        mu_legit = 1.0 - (2.0 / 3.0) * observed_noise_floor
        sigma_legit = max(0.02, np.sqrt(observed_noise_floor / 32.0))
        # z for 0.005 is approx 2.576
        z_crit = 2.576
        tau = mu_legit - z_crit * sigma_legit
        # Clamp to reasonable range
        return float(np.clip(tau, 0.70, 0.92))

    def evaluate(self, measured_fidelity: float, n_qubits: int = 8, noise_floor: float = 0.02) -> Dict[str, Any]:
        """Compute posterior probability P(Attacker | Fidelity) via Bayes rule."""
        tau = self.calculate_dynamic_threshold(noise_floor)
        
        # Likelihood parameters
        mu_legit = 1.0 - (2.0 / 3.0) * noise_floor
        sigma_legit = 0.04
        
        mu_attack = 0.75 - (2.0 / 3.0) * noise_floor
        sigma_attack = 0.09
        
        # Gaussian densities
        p_f_given_legit = (1.0 / (sigma_legit * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((measured_fidelity - mu_legit) / sigma_legit) ** 2)
        p_f_given_attack = (1.0 / (sigma_attack * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((measured_fidelity - mu_attack) / sigma_attack) ** 2)
        
        # Bayes calculation
        prior_l = 1.0 - self.prior_attack
        p_f_total = p_f_given_attack * self.prior_attack + p_f_given_legit * prior_l
        
        if p_f_total < 1e-12:
            posterior_attack = 1.0 if measured_fidelity < tau else 0.0
        else:
            posterior_attack = (p_f_given_attack * self.prior_attack) / p_f_total
            
        posterior_attack = float(np.clip(posterior_attack, 0.0, 1.0))
        
        is_threat = measured_fidelity < tau or posterior_attack > 0.80
        severity = "CRITICAL" if posterior_attack > 0.95 else ("HIGH" if is_threat else "LOW")
        
        return {
            "fidelity": measured_fidelity,
            "threshold": tau,
            "posterior_attack_prob": posterior_attack,
            "is_threat": is_threat,
            "severity": severity,
            "decision": "ALARM_TRIGGERED" if is_threat else "LEGITIMATE_VERIFIED"
        }
