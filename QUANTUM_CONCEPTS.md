# Quantum Information Concepts & Laboratory Mathematics

This document details the mathematical models and simulations implemented in the QuantumGuard Quantum Laboratory (`quantum_honeypot/core/` and `quantum_honeypot/api/quantum_router.py`).

---

## 1. Qubit Statevector & Bloch Sphere Representation

A pure single-qubit state $|\psi\rangle$ is represented as a normalized vector in a two-dimensional complex Hilbert space:

$$|\psi\rangle = \alpha |0\rangle + \beta |1\rangle = \cos\left(\frac{\theta}{2}\right) |0\rangle + e^{i\phi}\sin\left(\frac{\theta}{2}\right) |1\rangle$$

where $\theta \in [0, \pi]$ is the polar angle and $\phi \in [0, 2\pi)$ is the azimuthal angle on the Bloch sphere.

### Bloch Sphere Coordinates
The Cartesian coordinates $(u, v, w)$ of the Bloch vector correspond to the expectation values of the Pauli operators:
- $u = \langle \sigma_x \rangle = 2\text{Re}(\alpha^* \beta) = \sin\theta \cos\phi$
- $v = \langle \sigma_y \rangle = 2\text{Im}(\alpha^* \beta) = \sin\theta \sin\phi$
- $w = \langle \sigma_z \rangle = |\alpha|^2 - |\beta|^2 = \cos\theta$

---

## 2. Quantum Gates & Unitary Evolution

Every quantum gate is represented by a unitary operator $U$ satisfying $U^\dagger U = I$:

- **Hadamard ($H$)**: Creates equal superposition
  $$H = \frac{1}{\sqrt{2}} \begin{pmatrix} 1 & 1 \\ 1 & -1 \end{pmatrix}$$
- **Pauli-X**: Bit flip ($|0\rangle \leftrightarrow |1\rangle$)
  $$X = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}$$
- **Pauli-Z**: Phase flip ($|1\rangle \to -|1\rangle$)
  $$Z = \begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}$$
- **Controlled-NOT ($\text{CNOT}$)**: Two-qubit entangling gate
  $$\text{CNOT} = |0\rangle\langle 0| \otimes I + |1\rangle\langle 1| \otimes X$$

---

## 3. Bell State & CHSH Inequality Violation

For the maximally entangled Bell state:
$$|\Phi^+\rangle = \frac{1}{\sqrt{2}}(|00\rangle + |11\rangle)$$

Measurement along direction $\theta_a$ by Alice and $\theta_b$ by Bob yields correlation expectation:
$$E(a, b) = \cos(\theta_a - \theta_b)$$

Under optimal CHSH measurement angles:
- Alice: $a_1 = 0$, $a_2 = \frac{\pi}{2}$
- Bob: $b_1 = \frac{\pi}{4}$, $b_2 = \frac{3\pi}{4}$

The Clauser-Horne-Shimony-Holt (CHSH) parameter $S$ is:
$$S = |E(a_1, b_1) - E(a_1, b_2) + E(a_2, b_1) + E(a_2, b_2)|$$

- **Classical Local Hidden Variable Bound**: $S \le 2.0$
- **Tsirelson Quantum Bound**: $S = 2\sqrt{2} \approx 2.8284$

A measured value of $S > 2.0$ demonstrates quantum non-locality under Bell assumptions.

---

## 4. No-Cloning Theorem & UQCM Bound

The No-Cloning Theorem (Wootters & Zurek, 1982) dictates that no unitary transformation can map $|\psi\rangle|0\rangle \to |\psi\rangle|\psi\rangle$ for an arbitrary unknown state $|\psi\rangle$.

Optimal 1-to-2 Universal Quantum Cloning Machines (UQCM, Bužek & Hillery, 1996) are strictly bounded by:
$$F_{\text{UQCM}} = \frac{5}{6} \approx 0.8333$$

> [!NOTE]
> **Scientific Integrity**: The No-Cloning theorem is a law governing physical quantum states. It does **not** prevent an attacker from copying classical text files, passwords, or credentials stored on a computer.

---

## 5. BB84 Quantum Key Distribution (QKD)

In the BB84 protocol (Bennett & Brassard, 1984):
1. **Preparation**: Alice sends qubits encoded in randomly chosen bases: Rectilinear $+$ ($\{|0\rangle, |1\rangle\}$) or Diagonal $\times$ ($\{|+\rangle, |-\rangle\}$).
2. **Measurement**: Bob measures in independently chosen bases.
3. **Sifting**: Alice and Bob publicly share basis choices; measurements where bases matched are retained.
4. **Intrusion Detection via QBER**:
   - If an eavesdropper (Eve) intercepts and resends qubits, non-orthogonal state collapse induces a theoretical **25% Quantum Bit Error Rate (QBER)** on sifted bits.
   - If QBER exceeds the security threshold ($\approx 11\%$), the session is aborted.

The simulator estimates QBER from sifted bits and reports a 95% Wilson
interval. If QBER reaches the configured threshold (default 11%), the
educational session discards its candidate key. With independently random
preparation, interception, and measurement bases, full random-basis
intercept-resend gives expected sifted-key QBER 25% in the ideal asymptotic
model. Finite samples fluctuate. This simplified simulator is not a composable
security proof, an authenticated protocol, or production QKD.

---

## 6. Noise Channels and State Metrics

The API's `/api/v1/quantum/noise` operation starts with a pure density matrix
$\rho = |\psi\rangle\langle\psi|$ and applies a completely positive,
trace-preserving map $\mathcal{E}(\rho) = \sum_k K_k \rho K_k^\dagger$.
The implemented Kraus operators satisfy $\sum_k K_k^\dagger K_k = I$:

- Bit flip: $\{\sqrt{1-p}I,\sqrt{p}X\}$.
- Phase flip: $\{\sqrt{1-p}I,\sqrt{p}Z\}$.
- Depolarizing: $\{\sqrt{1-p}I,\sqrt{p/3}X,\sqrt{p/3}Y,\sqrt{p/3}Z\}$.
- Amplitude damping: $K_0=\mathrm{diag}(1,\sqrt{1-p})$, with decay operator
  $K_1=\begin{pmatrix}0&\sqrt p\\0&0\end{pmatrix}$.
- Phase damping: $K_0=\mathrm{diag}(1,\sqrt{1-p})$ and
  $K_1=\mathrm{diag}(0,\sqrt p)$.

Purity is $\mathrm{Tr}(\rho^2)$; because the input is pure, state fidelity is
$\langle\psi|\rho_{\mathrm{out}}|\psi\rangle$. Responses report trace and
minimum eigenvalue as numerical validity checks. The three-qubit repetition
demonstrations correct only the corresponding single bit- or phase-flip error;
they do not correct arbitrary quantum errors.

## 7. Quantum Teleportation

The simulator prepares an input qubit and $|\Phi^+\rangle$, applies the
Bell-measurement circuit, conditions on both measured classical bits, and
applies $X^{m_1}Z^{m_0}$ to Bob's qubit. It combines corrected branches into an
output density matrix and compares it with the original pure state. Ideal
statevector simulation yields unit fidelity up to floating-point error.
Teleportation requires two classical bits and an entangled pair; it neither
copies an unknown state nor transmits information faster than light.

## 8. Grover Search Benchmark

For $N=2^n$ candidates and $M$ marked states, let
$\theta=\arcsin\sqrt{M/N}$. After $r$ Grover iterations the success probability
is $\sin^2((2r+1)\theta)$; the selected iteration count is the nearest
non-negative integer to $\pi/(4\theta)-1/2$. Repeated seeded Bernoulli trials
estimate that theoretical probability. The classical comparison assumes
random sequential search without replacement and known $M$, with expected
queries $(N+1)/(M+1)$.

The asymptotic $O(\sqrt{N/M})$ advantage is an oracle-query statement. Reported
Python sampling time measures simulator bookkeeping only; it is not quantum
hardware runtime or evidence of practical hardware advantage.
