"""Unit tests for Quantum Laboratory and mathematical calculations."""

import math
import pytest
from quantum_honeypot.core.quantum_lab import QuantumLab

def test_single_qubit_bloch_normalization():
    res = QuantumLab.single_qubit_bloch(theta=math.pi / 2, phi=0.0)
    p0 = res["probabilities"]["|0>"]
    p1 = res["probabilities"]["|1>"]
    assert pytest.approx(p0 + p1, abs=1e-5) == 1.0
    assert pytest.approx(res["purity"], abs=1e-5) == 1.0
    coords = res["bloch_coordinates"]
    # For theta=pi/2, phi=0, Bloch vector is on x-axis (x=1, y=0, z=0)
    assert pytest.approx(coords["x"], abs=1e-4) == 1.0
    assert pytest.approx(coords["y"], abs=1e-4) == 0.0
    assert pytest.approx(coords["z"], abs=1e-4) == 0.0

def test_quantum_circuit_simulation_bell_state():
    # Circuit: H(q0), CNOT(q0, q1) -> produces (|00> + |11>)/sqrt(2)
    gates = [
        {"gate": "H", "target": 0},
        {"gate": "CNOT", "control": 0, "target": 1}
    ]
    res = QuantumLab.simulate_circuit(n_qubits=2, gate_list=gates, shots=2000)
    counts = res["counts"]
    # Only "00" and "11" should appear (with minor statistical fluctuation)
    assert "00" in counts
    assert "11" in counts
    total_bell = counts.get("00", 0) + counts.get("11", 0)
    assert total_bell == 2000
    assert abs(counts["00"] - counts["11"]) < 250  # Balanced distribution

def test_bell_chsh_violation():
    # Ideal Bell state violation should exceed classical bound 2.0
    res = QuantumLab.bell_chsh_experiment(trials=2000, noise=0.0)
    assert res["chsh_parameter_S"] > 2.0
    assert res["violates_classical_bound"] is True
    assert pytest.approx(res["theoretical_S"], abs=0.05) == 2.0 * math.sqrt(2.0)

def test_bb84_protocol_interception_detection():
    # Without Eve, QBER is 0
    clean_res = QuantumLab.bb84_simulation(num_bits=100, eve_intercept=False, noise_rate=0.0)
    assert clean_res["qber"] == 0.0
    assert clean_res["channel_secure"] is True

    # With Eve intercepting, QBER is approximately 25% (>= 15%)
    eve_res = QuantumLab.bb84_simulation(num_bits=200, eve_intercept=True, noise_rate=0.0)
    assert eve_res["qber"] >= 0.15
    assert eve_res["channel_secure"] is False

def test_grover_search_probability_amplification():
    # 3-qubit database (8 items), target item = 5
    res = QuantumLab.grover_search(num_qubits=3, target_state=5)
    assert res["success_probability"] > 0.85
    assert res["target_binary"] == "101"
