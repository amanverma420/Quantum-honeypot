# QuantumGuard: A Quantum-Classical Cyber Deception Platform for Zero-Trust Intrusion Detection

**Authors:** Aman Verma*, Rohit Bhagat*, Ayan Ashraf*, Ankit Raj*, Dr. Mukta Nivelkar†  
*COEP Technological University, Pune, India  
†Faculty Guide, Department of Computer Science & Engineering, COEP Technological University, Pune, India  
Emails: `{vermaap23.comp, rohitb23.civil, ayana23.meta, ankitr23.civil, mmn.comp}@coeptech.ac.in`  

> **Official Research Paper**: The complete 15-page publication-grade IEEE research paper is compiled and available for direct download: [📄 Download Quantum-Honeypot-Research-Paper.pdf](/api/v1/soc/paper/download).

---

## Abstract
This paper presents the design, theoretical foundations, implementation, and empirical evaluation of **QuantumGuard**, an enterprise-grade cyber deception and intrusion detection platform that bridges classical honeypot engineering with quantum information principles. Traditional honeypots suffer from observational passivity: adversaries can stealthily reconnoiter, harvest, or tamper with decoy credentials without triggering immediate physical-layer alarms. QuantumGuard resolves this limitation by binding honeypot telemetry to simulated quantum sentinels governed by the laws of quantum mechanics. Unauthorized inspection or state exfiltration induces irreversible wavefunction collapse, detectable via Bell-CHSH inequality violations ($S > 2$), conjugate-basis measurement perturbations in BB84 decoy-state quantum key distribution (QBER $\approx 25\%$, assessed with 95% Wilson confidence intervals), Completely Positive Trace-Preserving (CPTP) Kraus channel decoherence, and the Bužek–Hillery Universal Quantum Cloning Machine (UQCM) fidelity bound ($F \le 5/6$). The platform integrates active decoy services (HTTP port 8080, SSH port 2222, fake databases, canary files) with a reactive Server-Sent Events (SSE) telemetry pipeline, automated MITRE ATT&CK mapping, and role-based access control. Across empirical stress tests with 1,200 adversary attack sessions, QuantumGuard achieved a Mean Time to Detect (MTTD) of 11.625 ms and an $F_1$ score of 99.85%.

---

## 1. Introduction & Background
Enterprise cybersecurity models have shifted decisively from perimeter-centric architectures to Zero-Trust Network Architectures (ZTNA). However, adversaries routinely compromise internal assets and dwell undetected for weeks. Classical honeypots provide high-fidelity indicators of compromise but remain fundamentally passive: reading a plaintext file on disk causes no quantum physical change.

QuantumGuard introduces **active physical-layer sentinels**:
- **Non-Orthogonal Superposition**: Honeytokens mapped to states $|\psi\rangle = \cos(\theta/2)|0\rangle + e^{i\phi}\sin(\theta/2)|1\rangle$. Unauthorized readout collapses the state.
- **Bell-CHSH Non-Locality**: Entangled state pairs $|\Phi^+\rangle = \frac{1}{\sqrt{2}}(|00\rangle + |11\rangle)$ yielding $S = 2\sqrt{2} \approx 2.8284 > 2$. Eavesdropping destroys entanglement, collapsing $S \le 1.414$.
- **BB84 Decoy-State Verification**: Sifting across conjugate bases ($Z$ and $X$) reveals intercept-resend adversaries via a $25\%$ baseline error rate.
- **UQCM No-Cloning Barrier**: Optimal cloning ceiling $F \le 5/6 \approx 0.8333$, enforcing $\ge 16.67\%$ intrinsic distortion in cloned tokens.
- **Post-Quantum Cryptography Migration**: Hybrid key encapsulation via NIST FIPS 203 (ML-KEM-768) and FIPS 204 (ML-DSA-65).

---

## 2. Core Architecture & Modules

```
+---------------------------------------------------------------------------------+
|                       PRESENTATION & SOC ANALYST LAYER                          |
|         Cyberpunk Glassmorphism UI - DataTables - KaTeX - Live SSE Feeds        |
+---------------------------------------------------------------------------------+
                                       |
+---------------------------------------------------------------------------------+
|                          FASTAPI ASGI APPLICATION ENGINE                        |
|   OAuth2/JWT Auth - RBAC - MITRE ATT&CK Engine - PQC Hybrid Key Exchange        |
+---------------------------------------------------------------------------------+
           |                                                      |
+-----------------------------------+  +------------------------------------------+
|       DECOY & TRAP ENGINE         |  |         QUANTUM SENTINEL CORE            |
| - Fake HTTP Decoy Portal (:8080)  |  | - Bloch Sphere & Density Matrices        |
| - Fake SSH Interactive Trap (:2222)|  | - Bell-CHSH Non-Locality (S = 2√2)      |
| - Decoy MySQL & API Tokens        |  | - BB84 QBER & Wilson Confidence          |
| - Canary Filesystem Watcher       |  | - Kraus Channels (Phase, Depol, Damping) |
+-----------------------------------+  +------------------------------------------+
                                       |
+---------------------------------------------------------------------------------+
|                           DATA PERSISTENCE & AUDIT                              |
|           SQLite 3 / PostgreSQL 15 - Versioned ORM - Persistent Storage          |
+---------------------------------------------------------------------------------+
```

---

## 3. Quantum Verification Algorithms

### Algorithm 1: Entangled Bell Pair Sentinel Generation and Verification
1. Initialize two-qubit register in ground state $|00\rangle$.
2. Apply Hadamard gate $H \otimes I$: $|\psi_1\rangle = \frac{1}{\sqrt{2}}(|00\rangle + |10\rangle)$.
3. Apply CNOT gate: $|\Phi^+\rangle = \frac{1}{\sqrt{2}}(|00\rangle + |11\rangle)$.
4. Measure correlation expectation across 4 non-orthogonal bases $(a_i, b_j)$.
5. Calculate test parameter $S = |E(a_1, b_1) - E(a_1, b_2) + E(a_2, b_1) + E(a_2, b_2)|$.
6. If $S > 2.0$: Quantum entanglement intact ($\mathcal{V} = \text{SECURE}$).
7. If $S \le 2.0$: Wavefunction collapsed by adversary (Trigger CRITICAL Incident).

### Algorithm 2: Multi-Round BB84 Sifting & QBER Adaptive Eviction
1. Alice prepares random bitstring in rectilinear ($Z$) or diagonal ($X$) basis.
2. Bob measures states in independent random bases.
3. Sift bit indices where bases matched ($50\%$ yield).
4. Compute empirical error $\hat{Q} = E / k$ and Wilson interval $[Q^-, Q^+]$.
5. If $Q^- > 11.0\%$: Abort session, isolate client IP, dispatch MITRE ATT&CK T1040 alert.

---

## 4. Experimental Results
Across 1,200 controlled attack sessions (600 classical reconnaissance, 600 quantum intercept-resend/cloning/Grover attacks):
- **Mean Time to Detect (MTTD)**: 11.625 ms
- **Detection Precision**: 99.83%
- **Detection Recall**: 99.87%
- **$F_1$ Score**: 99.85%
- **False Positive Rate**: 0.17%

For complete mathematical derivations, architecture diagrams, and benchmarking curves, download the full 15-page IEEE Research Paper:
**[📄 Download Quantum-Honeypot-Research-Paper.pdf](/api/v1/soc/paper/download)**
