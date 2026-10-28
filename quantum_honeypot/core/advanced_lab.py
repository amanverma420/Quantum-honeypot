"""Numerical experiments for noise, teleportation, and Grover benchmarking."""

import math
import time
from typing import Any

import numpy as np


_I = np.eye(2, dtype=complex)
_X = np.array([[0, 1], [1, 0]], dtype=complex)
_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
_Z = np.array([[1, 0], [0, -1]], dtype=complex)
_H = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)


def _bloch(rho: np.ndarray) -> dict[str, float]:
    return {
        "x": float(np.real(np.trace(rho @ _X))),
        "y": float(np.real(np.trace(rho @ _Y))),
        "z": float(np.real(np.trace(rho @ _Z))),
    }


def _density_payload(rho: np.ndarray) -> list[list[dict[str, float]]]:
    return [
        [
            {"real": float(np.real(value)), "imag": float(np.imag(value))}
            for value in row
        ]
        for row in rho
    ]


def noise_experiment(theta: float, phi: float, channel: str, probability: float) -> dict[str, Any]:
    """Apply a trace-preserving single-qubit channel to a pure input state."""
    alpha = math.cos(theta / 2)
    beta = complex(math.cos(phi), math.sin(phi)) * math.sin(theta / 2)
    state = np.array([alpha, beta], dtype=complex)
    rho = np.outer(state, state.conj())
    p = probability

    if channel in ("bit_flip", "phase_flip"):
        operator = _X if channel == "bit_flip" else _Z
        kraus = [math.sqrt(1 - p) * _I, math.sqrt(p) * operator]
    elif channel == "depolarizing":
        kraus = [
            math.sqrt(1 - p) * _I,
            math.sqrt(p / 3) * _X,
            math.sqrt(p / 3) * _Y,
            math.sqrt(p / 3) * _Z,
        ]
    elif channel == "amplitude_damping":
        kraus = [
            np.array([[1, 0], [0, math.sqrt(1 - p)]], dtype=complex),
            np.array([[0, math.sqrt(p)], [0, 0]], dtype=complex),
        ]
    elif channel == "phase_damping":
        kraus = [
            np.array([[1, 0], [0, math.sqrt(1 - p)]], dtype=complex),
            np.array([[0, 0], [0, math.sqrt(p)]], dtype=complex),
        ]
    else:
        raise ValueError(f"Unsupported noise channel: {channel}")

    noisy = sum((operator @ rho @ operator.conj().T for operator in kraus), np.zeros((2, 2), dtype=complex))
    fidelity = float(np.real(np.vdot(state, noisy @ state)))
    eigenvalues = np.linalg.eigvalsh(noisy)
    return {
        "channel": channel,
        "probability": p,
        "input_state": {"theta": theta, "phi": phi},
        "density_matrix": _density_payload(noisy),
        "trace": float(np.real(np.trace(noisy))),
        "minimum_eigenvalue": float(np.min(eigenvalues)),
        "fidelity": min(1.0, max(0.0, fidelity)),
        "purity": float(np.real(np.trace(noisy @ noisy))),
        "bloch_before": _bloch(rho),
        "bloch_after": _bloch(noisy),
        "scientific_note": "Fidelity is <psi|rho_after|psi> for the pure input state; the channels are single-qubit CPTP maps.",
    }


def _single_qubit_operator(n_qubits: int, target: int, gate: np.ndarray) -> np.ndarray:
    operator = np.array([[1]], dtype=complex)
    for index in range(n_qubits):
        operator = np.kron(operator, gate if index == target else _I)
    return operator


def _controlled_not(n_qubits: int, control: int, target: int) -> np.ndarray:
    dimension = 2**n_qubits
    result = np.zeros((dimension, dimension), dtype=complex)
    for basis in range(dimension):
        bits = list(f"{basis:0{n_qubits}b}")
        if bits[control] == "1":
            bits[target] = "0" if bits[target] == "1" else "1"
        result[int("".join(bits), 2), basis] = 1
    return result


def teleportation_experiment(theta: float, phi: float) -> dict[str, Any]:
    """Run the standard three-qubit teleportation circuit and average its branches."""
    alpha = math.cos(theta / 2)
    beta = complex(math.cos(phi), math.sin(phi)) * math.sin(theta / 2)
    input_state = np.array([alpha, beta], dtype=complex)
    initial = np.kron(np.kron(input_state, np.array([1, 0], dtype=complex)), np.array([1, 0], dtype=complex))
    state = _controlled_not(3, 1, 2) @ (_single_qubit_operator(3, 1, _H) @ initial)
    state = _single_qubit_operator(3, 0, _H) @ (_controlled_not(3, 0, 1) @ state)

    reconstructed = np.zeros((2, 2), dtype=complex)
    outcomes = []
    for bits in range(4):
        outcome = f"{bits:02b}"
        indices = [index for index in range(8) if index >> 1 == bits]
        branch = np.zeros(8, dtype=complex)
        branch[indices] = state[indices]
        probability = float(np.vdot(branch, branch).real)
        if probability < 1e-15:
            outcomes.append({"measurement": outcome, "classical_bits": outcome, "probability": 0.0})
            continue
        branch /= math.sqrt(probability)
        bob_base = bits << 1
        bob = np.array([branch[bob_base], branch[bob_base + 1]], dtype=complex)
        # Measurement bits are q0q1: apply X for q1 and Z for q0.
        if outcome[1] == "1":
            bob = _X @ bob
        if outcome[0] == "1":
            bob = _Z @ bob
        reconstructed += probability * np.outer(bob, bob.conj())
        outcomes.append({"measurement": outcome, "classical_bits": outcome, "probability": probability})

    fidelity = float(np.real(np.vdot(input_state, reconstructed @ input_state)))
    return {
        "input_statevector": [{"real": float(v.real), "imag": float(v.imag)} for v in input_state],
        "measurement_outcomes": outcomes,
        "classical_bits_sent": "two measurement bits (m0,m1) per run; correction X^m1 Z^m0",
        "reconstructed_density_matrix": _density_payload(reconstructed),
        "fidelity": min(1.0, max(0.0, fidelity)),
        "bloch_input": _bloch(np.outer(input_state, input_state.conj())),
        "bloch_reconstructed": _bloch(reconstructed),
        "entanglement": "Alice and Bob share a |Phi+> Bell pair prepared by H and CNOT.",
        "scientific_note": "Ideal statevector simulation; teleportation requires two classical bits and does not permit faster-than-light signaling or state cloning.",
    }


def bell_state_experiment(shots: int, seed: int | None = None) -> dict[str, Any]:
    """Prepare |Phi+> and report its computational-basis sample and entanglement."""
    initial = np.array([1, 0, 0, 0], dtype=complex)
    state = _controlled_not(2, 0, 1) @ (_single_qubit_operator(2, 0, _H) @ initial)
    amplitudes = state.reshape((2, 2))
    reduced = amplitudes @ amplitudes.conj().T
    concurrence = float(2 * abs(state[0] * state[3] - state[1] * state[2]))
    rng = np.random.default_rng(seed)
    probabilities = np.abs(state) ** 2
    sampled = rng.choice(4, size=shots, p=probabilities)
    counts = {format(index, "02b"): int(np.count_nonzero(sampled == index)) for index in range(4)}
    return {
        "state": "|Phi+> prepared by H(q0), CNOT(q0,q1)",
        "statevector": [{"real": float(value.real), "imag": float(value.imag)} for value in state],
        "measurement_probabilities": {format(index, "02b"): float(probabilities[index]) for index in range(4)},
        "sample_counts": counts,
        "shots": shots,
        "reduced_density_matrix": _density_payload(reduced),
        "reduced_state_purity": float(np.real(np.trace(reduced @ reduced))),
        "concurrence": concurrence,
        "entangled": concurrence > 1e-12,
        "scientific_note": "The reduced single-qubit state is maximally mixed (purity 1/2); the pure two-qubit Bell state has concurrence 1.",
    }


def grover_benchmark(
    num_qubits: int,
    marked_states: list[int],
    trials: int,
    seed: int | None = None,
) -> dict[str, Any]:
    """Compare amplitude amplification probability with seeded measurement trials."""
    size = 2**num_qubits
    marked = sorted(set(marked_states))
    if not marked or any(index < 0 or index >= size for index in marked):
        raise ValueError("marked_states must contain unique in-range search indices")
    marked_count = len(marked)
    theta = math.asin(math.sqrt(marked_count / size))
    iterations = 0 if marked_count == size else max(0, round(math.pi / (4 * theta) - 0.5))
    started = time.perf_counter()
    state = np.ones(size, dtype=complex) / math.sqrt(size)
    for _ in range(iterations):
        state[marked] *= -1
        state = 2 * np.mean(state) - state
    theoretical = float(np.sum(np.abs(state[marked]) ** 2))
    formula_probability = math.sin((2 * iterations + 1) * theta) ** 2
    rng = np.random.default_rng(seed)
    successes = int(rng.binomial(trials, theoretical))
    elapsed = time.perf_counter() - started
    classical_expected = (size + 1) / (marked_count + 1)
    return {
        "search_space_size": size,
        "marked_item_count": marked_count,
        "marked_states": marked,
        "grover_iterations": iterations,
        "theoretical_success_probability": theoretical,
        "amplitude_amplification_formula_probability": formula_probability,
        "empirical_success_probability": successes / trials,
        "successful_trials": successes,
        "trials": trials,
        "quantum_oracle_queries": iterations,
        "classical_expected_queries": classical_expected,
        "classical_query_assumption": "Random sequential search without replacement; marked-item count is known, and each oracle query tests one candidate.",
        "simulation_seconds": elapsed,
        "query_complexity_note": "Grover uses O(sqrt(N/M)) oracle queries for M marked items; simulator wall time is not a hardware runtime or practical speedup claim.",
    }


def repetition_code_experiment(code: str, logical_bit: int, error_qubit: int) -> dict[str, Any]:
    """Demonstrate the three-qubit repetition code for bit or phase errors."""
    if code not in ("bit_flip", "phase_flip"):
        raise ValueError("code must be bit_flip or phase_flip")
    if logical_bit not in (0, 1) or error_qubit not in (0, 1, 2):
        raise ValueError("logical_bit must be 0 or 1 and error_qubit must be 0, 1, or 2")
    if code == "bit_flip":
        bits = [logical_bit] * 3
        bits[error_qubit] ^= 1
        syndrome = [bits[0] ^ bits[1], bits[1] ^ bits[2]]
        correction_index = {(1, 0): 0, (1, 1): 1, (0, 1): 2}.get(tuple(syndrome))
        if correction_index is not None:
            bits[correction_index] ^= 1
        recovered = bits[0] == logical_bit
        encoded_state = f"|{logical_bit}{logical_bit}{logical_bit}>"
        stabilizers = "ZZ on qubits (0,1) and (1,2)"
        correction_gate = "X"
        syndrome = [int(value) for value in syndrome]
        recovered_measurement = bits
    else:
        # Phase codewords are |+++> and |--->. Z errors anticommute
        # with neighboring XX stabilizers in the same pattern as bit-code X errors.
        syndrome_by_qubit = {0: (1, 0), 1: (1, 1), 2: (0, 1)}
        syndrome = list(syndrome_by_qubit[error_qubit])
        correction_index = {(1, 0): 0, (1, 1): 1, (0, 1): 2}[tuple(syndrome)]
        recovered = True
        encoded_state = "|+++>" if logical_bit == 0 else "|--->"
        stabilizers = "XX on qubits (0,1) and (1,2)"
        correction_gate = "Z"
        recovered_measurement = None
    return {
        "code": code,
        "logical_bit": logical_bit,
        "encoded_logical_state": encoded_state,
        "stabilizers": stabilizers,
        "error_qubit": error_qubit,
        "syndrome": syndrome,
        "correction_qubit": correction_index,
        "correction_gate": correction_gate,
        "encoded_measurement_after_recovery": recovered_measurement,
        "recovered_logical_bit": logical_bit if recovered else None,
        "recovered": recovered,
        "limitation": "The three-qubit repetition code corrects only the corresponding single bit-flip or phase-flip error, not arbitrary single-qubit errors.",
    }
