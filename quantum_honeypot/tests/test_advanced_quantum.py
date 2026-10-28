"""Numerical and statistical validation for advanced quantum experiments."""

import math

import numpy as np
import pytest

from quantum_honeypot.core.advanced_lab import (
    bell_state_experiment,
    grover_benchmark,
    noise_experiment,
    repetition_code_experiment,
    teleportation_experiment,
)
from quantum_honeypot.core.quantum_lab import QuantumLab


@pytest.mark.parametrize(
    "channel",
    ["bit_flip", "phase_flip", "depolarizing", "amplitude_damping", "phase_damping"],
)
def test_noise_channels_preserve_density_matrix_properties(channel):
    result = noise_experiment(math.pi / 2, math.pi / 3, channel, 0.37)
    matrix = np.array(
        [[complex(cell["real"], cell["imag"]) for cell in row] for row in result["density_matrix"]]
    )
    assert result["trace"] == pytest.approx(1.0, abs=1e-12)
    assert np.allclose(matrix, matrix.conj().T)
    assert np.linalg.eigvalsh(matrix).min() >= -1e-12
    assert 0.0 <= result["fidelity"] <= 1.0
    assert 0.5 <= result["purity"] <= 1.0


@pytest.mark.parametrize("theta,phi", [(0, 0), (math.pi, 0), (math.pi / 2, 1.3), (2.1, 4.8)])
def test_teleportation_runs_circuit_and_reconstructs_input(theta, phi):
    result = teleportation_experiment(theta, phi)
    assert result["fidelity"] == pytest.approx(1.0, abs=1e-12)
    assert sum(outcome["probability"] for outcome in result["measurement_outcomes"]) == pytest.approx(1.0)
    assert all(outcome["probability"] == pytest.approx(0.25, abs=1e-12)
               for outcome in result["measurement_outcomes"])


def test_bell_state_has_maximal_entanglement_and_expected_measurements():
    result = bell_state_experiment(shots=2048, seed=13)
    assert result["entangled"] is True
    assert result["concurrence"] == pytest.approx(1.0, abs=1e-12)
    assert result["reduced_state_purity"] == pytest.approx(0.5)
    assert result["measurement_probabilities"]["00"] == pytest.approx(0.5)
    assert result["measurement_probabilities"]["01"] == pytest.approx(0.0)
    assert result["measurement_probabilities"]["10"] == pytest.approx(0.0)
    assert result["measurement_probabilities"]["11"] == pytest.approx(0.5)
    assert result["sample_counts"]["01"] == result["sample_counts"]["10"] == 0


@pytest.mark.parametrize("code", ["bit_flip", "phase_flip"])
@pytest.mark.parametrize("logical_bit", [0, 1])
@pytest.mark.parametrize("error_qubit", [0, 1, 2])
def test_repetition_code_corrects_single_matching_error(code, logical_bit, error_qubit):
    result = repetition_code_experiment(code, logical_bit, error_qubit)
    assert result["recovered"] is True
    assert result["recovered_logical_bit"] == logical_bit
    assert result["correction_qubit"] == error_qubit


def test_bb84_intercept_resend_qber_is_emergent_and_reproducible():
    kwargs = dict(num_bits=20000, eve_intercept=True, eve_probability=1.0, seed=441)
    first = QuantumLab.bb84_simulation(**kwargs)
    second = QuantumLab.bb84_simulation(**kwargs)
    assert first["qber"] == second["qber"]
    assert 0.20 <= first["qber"] <= 0.30
    assert first["channel_secure"] is False
    assert first["final_key"] == ""


def test_bb84_ideal_channel_has_no_sifted_key_errors():
    result = QuantumLab.bb84_simulation(num_bits=1000, seed=9)
    assert result["qber"] == 0.0
    assert result["channel_secure"] is True
    assert result["candidate_key_material"] == result["alice_sifted_key"]
    assert result["final_key"] == ""


def test_grover_benchmark_supports_multiple_marked_states_and_seed():
    kwargs = dict(num_qubits=3, marked_states=[1, 5], trials=4000, seed=71)
    first = grover_benchmark(**kwargs)
    second = grover_benchmark(**kwargs)
    assert first["grover_iterations"] == 1
    assert first["theoretical_success_probability"] == pytest.approx(1.0, abs=1e-12)
    assert first["empirical_success_probability"] == second["empirical_success_probability"] == 1.0
    assert first["search_space_size"] == 8
    assert first["marked_item_count"] == 2


def test_noise_rejects_unknown_channel():
    with pytest.raises(ValueError):
        noise_experiment(0.0, 0.0, "unsupported", 0.2)
