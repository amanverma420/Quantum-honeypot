"""Comprehensive Quantum Simulation Engine for Educational and Research Laboratory."""

import math
import random
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

class QuantumLab:
    @staticmethod
    def single_qubit_bloch(theta: float, phi: float, apply_gate: Optional[str] = None) -> Dict[str, Any]:
        """Compute statevector, probabilities, and Bloch sphere coordinates."""
        # Initial state: |psi> = cos(theta/2)|0> + exp(i*phi)*sin(theta/2)|1>
        alpha = complex(math.cos(theta / 2.0), 0.0)
        beta = complex(math.sin(theta / 2.0) * math.cos(phi), math.sin(theta / 2.0) * math.sin(phi))
        state = np.array([alpha, beta], dtype=complex)

        # Gate definitions
        gates = {
            "I": np.eye(2, dtype=complex),
            "X": np.array([[0, 1], [1, 0]], dtype=complex),
            "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
            "Z": np.array([[1, 0], [0, -1]], dtype=complex),
            "H": (1.0 / np.sqrt(2.0)) * np.array([[1, 1], [1, -1]], dtype=complex),
            "S": np.array([[1, 0], [0, 1j]], dtype=complex),
            "T": np.array([[1, 0], [0, np.exp(1j * np.pi / 4.0)]], dtype=complex),
        }

        if apply_gate and apply_gate in gates:
            state = gates[apply_gate] @ state

        # Normalize numerically
        norm = np.linalg.norm(state)
        if norm > 1e-12:
            state = state / norm

        a, b = state[0], state[1]
        p0 = float(abs(a) ** 2)
        p1 = float(abs(b) ** 2)

        # Density matrix rho = |psi><psi|
        rho = np.outer(state, np.conj(state))

        # Bloch coordinates: u = 2 Re(a* b), v = 2 Im(a* b), w = |a|^2 - |b|^2
        u = float(2.0 * np.real(np.conj(a) * b))
        v = float(2.0 * np.imag(np.conj(a) * b))
        w = float(abs(a) ** 2 - abs(b) ** 2)

        return {
            "theta": float(theta),
            "phi": float(phi),
            "applied_gate": apply_gate,
            "statevector": [
                {"real": float(np.real(a)), "imag": float(np.imag(a))},
                {"real": float(np.real(b)), "imag": float(np.imag(b))}
            ],
            "probabilities": {"|0>": p0, "|1>": p1},
            "bloch_coordinates": {"x": u, "y": v, "z": w},
            "purity": float(np.real(np.trace(rho @ rho)))
        }

    @staticmethod
    def simulate_circuit(
        n_qubits: int,
        gate_list: List[Dict[str, Any]],
        shots: int = 1024,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Simulate an arbitrary multi-qubit circuit up to 8 qubits."""
        dim = 2 ** n_qubits
        state = np.zeros(dim, dtype=complex)
        state[0] = 1.0  # |00...0>

        # Standard 2x2 gates
        g1 = {
            "I": np.eye(2, dtype=complex),
            "X": np.array([[0, 1], [1, 0]], dtype=complex),
            "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
            "Z": np.array([[1, 0], [0, -1]], dtype=complex),
            "H": (1.0 / np.sqrt(2.0)) * np.array([[1, 1], [1, -1]], dtype=complex),
            "S": np.array([[1, 0], [0, 1j]], dtype=complex),
            "T": np.array([[1, 0], [0, np.exp(1j * np.pi / 4.0)]], dtype=complex)
        }

        for item in gate_list:
            g_name = item.get("gate", "").upper()
            target = item.get("target", 0)

            if g_name in g1 and 0 <= target < n_qubits:
                # Construct 2^n x 2^n operator via Kronecker product
                op = np.array([[1]], dtype=complex)
                for q in range(n_qubits):
                    if q == target:
                        op = np.kron(op, g1[g_name])
                    else:
                        op = np.kron(op, np.eye(2, dtype=complex))
                state = op @ state

            elif g_name == "CNOT":
                ctrl = item.get("control", 0)
                tgt = item.get("target", 1)
                if 0 <= ctrl < n_qubits and 0 <= tgt < n_qubits and ctrl != tgt:
                    # Construct CNOT operator
                    P0 = np.array([[1, 0], [0, 0]], dtype=complex)
                    P1 = np.array([[0, 0], [0, 1]], dtype=complex)
                    X = g1["X"]
                    I = np.eye(2, dtype=complex)

                    op0 = np.array([[1]], dtype=complex)
                    op1 = np.array([[1]], dtype=complex)
                    for q in range(n_qubits):
                        op0 = np.kron(op0, P0 if q == ctrl else I)
                        op1 = np.kron(op1, P1 if q == ctrl else (X if q == tgt else I))
                    state = (op0 + op1) @ state

            elif g_name == "SWAP":
                q1 = item.get("q1", 0)
                q2 = item.get("q2", 1)
                if 0 <= q1 < n_qubits and 0 <= q2 < n_qubits and q1 != q2:
                    # SWAP = CNOT(q1,q2) CNOT(q2,q1) CNOT(q1,q2)
                    pass # Handled by matrix permute
                    new_state = state.copy()
                    for i in range(dim):
                        b = list(f"{i:0{n_qubits}b}")
                        b[q1], b[q2] = b[q2], b[q1]
                        j = int("".join(b), 2)
                        new_state[j] = state[i]
                    state = new_state

        probs = np.abs(state) ** 2
        # Normalize probabilities for numerical safety
        total_p = np.sum(probs)
        if total_p > 0:
            probs = probs / total_p

        # Sample measurement shots
        indices = np.arange(dim)
        samples = np.random.default_rng(seed).choice(indices, size=shots, p=probs)
        counts = {}
        for idx in samples:
            b_str = f"{idx:0{n_qubits}b}"
            counts[b_str] = counts.get(b_str, 0) + 1

        state_repr = []
        for i in range(min(dim, 32)):
            if probs[i] > 1e-4:
                b_str = f"{i:0{n_qubits}b}"
                state_repr.append({
                    "basis": f"|{b_str}>",
                    "prob": float(probs[i]),
                    "amplitude": {"real": float(np.real(state[i])), "imag": float(np.imag(state[i]))}
                })

        return {
            "n_qubits": n_qubits,
            "gate_count": len(gate_list),
            "shots": shots,
            "seed": seed,
            "counts": counts,
            "active_states": state_repr
        }

    @staticmethod
    def bell_chsh_experiment(trials: int = 1000, noise: float = 0.0) -> Dict[str, Any]:
        """Perform simulated Bell-CHSH test with optimal measurement angles."""
        # Optimal angles for Bell state |Phi+> = (|00> + |11>)/sqrt(2):
        # Alice: a1 = 0, a2 = pi/2
        # Bob:   b1 = pi/4, b2 = 3*pi/4
        # Theoretical Quantum Bound: S = 2 * sqrt(2) ≈ 2.8284
        # Classical Local Realism Bound: S <= 2.0
        a1, a2 = 0.0, math.pi / 2.0
        b1, b2 = math.pi / 4.0, 3.0 * math.pi / 4.0

        def sample_pair(theta_a: float, theta_b: float, n: int) -> float:
            # Correlation for |Phi+> with measurement directions theta_a, theta_b:
            # P(same) = cos^2((theta_a - theta_b)/2)
            # P(diff) = sin^2((theta_a - theta_b)/2)
            # E = P(same) - P(diff) = cos(theta_a - theta_b)
            # Under depolarizing noise: E_noisy = (1 - noise) * cos(theta_a - theta_b)
            ideal_E = math.cos(theta_a - theta_b) * (1.0 - noise)
            p_same = (1.0 + ideal_E) / 2.0
            same_count = sum(1 for _ in range(n) if random.random() < p_same)
            diff_count = n - same_count
            return (same_count - diff_count) / float(n)

        e_a1_b1 = sample_pair(a1, b1, trials)
        e_a1_b2 = sample_pair(a1, b2, trials)
        e_a2_b1 = sample_pair(a2, b1, trials)
        e_a2_b2 = sample_pair(a2, b2, trials)

        # CHSH inequality parameter S = |E(a1, b1) - E(a1, b2) + E(a2, b1) + E(a2, b2)|
        # Note: with signs, standard optimal CHSH is E(a1,b1) - E(a1,b2) + E(a2,b1) + E(a2,b2)
        S = abs(e_a1_b1 - e_a1_b2 + e_a2_b1 + e_a2_b2)
        theoretical_S = 2.0 * math.sqrt(2.0) * (1.0 - noise)

        return {
            "trials_per_setting": trials,
            "noise_level": noise,
            "correlations": {
                "E(a1, b1)": round(e_a1_b1, 4),
                "E(a1, b2)": round(e_a1_b2, 4),
                "E(a2, b1)": round(e_a2_b1, 4),
                "E(a2, b2)": round(e_a2_b2, 4)
            },
            "chsh_parameter_S": round(S, 4),
            "theoretical_S": round(theoretical_S, 4),
            "classical_bound": 2.0,
            "tsirelson_quantum_bound": 2.8284,
            "violates_classical_bound": S > 2.0,
            "scientific_note": "A value of S > 2.0 refutes Local Hidden Variable theories under Bell assumptions."
        }

    @staticmethod
    def bb84_simulation(
        num_bits: int = 32,
        eve_intercept: bool = False,
        noise_rate: float = 0.0,
        eve_probability: float = 1.0,
        qber_threshold: float = 0.11,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Simulate BB84 Quantum Key Distribution protocol step by step."""
        rng = random.Random(seed)
        alice_bits = [rng.randint(0, 1) for _ in range(num_bits)]
        alice_bases = [rng.choice(["+", "x"]) for _ in range(num_bits)]
        bob_bases = [rng.choice(["+", "x"]) for _ in range(num_bits)]

        transmitted_bits = list(alice_bits)
        eve_bases: List[Optional[str]] = [None] * num_bits
        eve_measurements: List[Optional[int]] = [None] * num_bits
        intercepted = [False] * num_bits
        for i in range(num_bits):
            if eve_intercept and rng.random() < eve_probability:
                intercepted[i] = True
                eve_bases[i] = rng.choice(["+", "x"])
                eve_measurements[i] = (
                    alice_bits[i]
                    if eve_bases[i] == alice_bases[i]
                    else rng.randint(0, 1)
                )
                transmitted_bits[i] = eve_measurements[i]

        # Bob measures transmitted photons
        bob_bits = []
        for i in range(num_bits):
            source_basis = eve_bases[i] if intercepted[i] else alice_bases[i]
            if bob_bases[i] == source_basis:
                bit = transmitted_bits[i]
            else:
                bit = rng.randint(0, 1)
            if rng.random() < noise_rate:
                bit = 1 - bit
            bob_bits.append(bit)

        # Sifting phase: Alice and Bob publicly announce bases
        sifted_alice = []
        sifted_bob = []
        sifted_indices = []
        for i in range(num_bits):
            if alice_bases[i] == bob_bases[i]:
                sifted_indices.append(i)
                sifted_alice.append(alice_bits[i])
                sifted_bob.append(bob_bits[i])

        # Calculate Quantum Bit Error Rate (QBER)
        errors = sum(1 for a, b in zip(sifted_alice, sifted_bob) if a != b)
        qber = (errors / len(sifted_alice)) if sifted_alice else 0.0
        # Approximate Wilson interval communicates finite-sample uncertainty.
        n_sifted = len(sifted_alice)
        if n_sifted:
            z = 1.96
            denominator = 1 + z * z / n_sifted
            center = (qber + z * z / (2 * n_sifted)) / denominator
            margin = z * math.sqrt(qber * (1 - qber) / n_sifted + z * z / (4 * n_sifted**2)) / denominator
            qber_interval = [max(0.0, center - margin), min(1.0, center + margin)]
        else:
            qber_interval = [0.0, 1.0]
        secure = bool(n_sifted and qber < qber_threshold)

        steps_detail = []
        for i in range(min(num_bits, 16)):
            steps_detail.append({
                "index": i,
                "alice_bit": alice_bits[i],
                "alice_basis": alice_bases[i],
                "eve_intercepted": intercepted[i],
                "eve_basis": eve_bases[i] or "None",
                "bob_basis": bob_bases[i],
                "bob_bit": bob_bits[i],
                "basis_match": alice_bases[i] == bob_bases[i],
                "sifted": i in sifted_indices
            })

        return {
            "total_raw_bits": num_bits,
            "alice_raw_key": "".join(map(str, alice_bits)),
            "alice_bases": alice_bases,
            "bob_bases": bob_bases,
            "sifted_key_length": len(sifted_alice),
            "eve_intercepted": eve_intercept,
            "eve_interception_probability": eve_probability if eve_intercept else 0.0,
            "channel_noise_rate": noise_rate,
            "bit_errors": errors,
            "qber": round(qber, 4),
            "qber_95_confidence_interval": [round(value, 4) for value in qber_interval],
            "qber_threshold": qber_threshold,
            "channel_secure": secure,
            "experiment_accepted": secure,
            "alice_sifted_key": "".join(map(str, sifted_alice)),
            "bob_sifted_key": "".join(map(str, sifted_bob)),
            "candidate_key_material": "".join(map(str, sifted_alice)) if secure else "",
            "final_key": "",
            "key_status": (
                "candidate only; no error correction, privacy amplification, or authentication is implemented"
                if secure else "discarded by the configured QBER threshold"
            ),
            "preview_table": steps_detail,
            "scientific_note": (
                "In ideal BB84 with independently random bases, full random-basis intercept-resend "
                "produces an expected 25% QBER on sifted bits. This educational simulator is not a "
                "composable security proof or production QKD implementation."
            )
        }

    @staticmethod
    def grover_search(num_qubits: int = 3, target_state: int = 5) -> Dict[str, Any]:
        """Educational demonstration of Grover's quantum search algorithm."""
        dim = 2 ** num_qubits
        if not 0 <= target_state < dim:
            raise ValueError("target_state must be within the configured search space")
        
        # 1. Uniform superposition |s> = H^{\otimes n} |0>
        state = np.ones(dim, dtype=complex) / np.sqrt(dim)
        
        # Optimal number of Grover iterations: R ≈ (pi / 4) * sqrt(N)
        optimal_iters = max(1, int(round((math.pi / 4.0) * math.sqrt(dim))))

        history = [{"iteration": 0, "target_prob": float(abs(state[target_state]) ** 2)}]

        # Oracle O: flips sign of |target>
        # Diffusion D: 2|s><s| - I
        s_vec = np.ones((dim, 1), dtype=complex) / np.sqrt(dim)
        diffusion = 2.0 * (s_vec @ s_vec.T.conj()) - np.eye(dim, dtype=complex)

        for step in range(1, optimal_iters + 1):
            # Oracle reflection
            state[target_state] = -state[target_state]
            # Diffusion reflection
            state = diffusion @ state
            history.append({
                "iteration": step,
                "target_prob": float(abs(state[target_state]) ** 2)
            })

        final_probs = [float(abs(x) ** 2) for x in state]

        return {
            "num_qubits": num_qubits,
            "database_size": dim,
            "target_state_index": target_state,
            "target_binary": f"{target_state:0{num_qubits}b}",
            "optimal_iterations": optimal_iters,
            "success_probability": round(float(abs(state[target_state]) ** 2), 4),
            "iteration_history": history,
            "final_distribution": {f"|{i:0{num_qubits}b}>": round(final_probs[i], 4) for i in range(dim)}
        }
