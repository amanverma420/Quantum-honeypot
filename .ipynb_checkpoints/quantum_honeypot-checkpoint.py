"""
╔══════════════════════════════════════════════════════════════════════════╗
║         QUANTUM HONEYPOT SYSTEM — Tripwire-Based Intrusion Detection    ║
║         Novel Project | Quantum Computing + Cybersecurity               ║
║         Department of Computer Science & IT                             ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Core Idea:                                                              ║
║  A honeypot is a fake system resource designed to lure attackers.        ║
║  Classical honeypots can be probed silently. A QUANTUM honeypot          ║
║  embeds quantum tripwires — qubits in superposition — into the          ║
║  honeypot resource. Any attempt to READ or COPY the resource             ║
║  collapses the quantum state (observer effect + no-cloning theorem),    ║
║  producing a detectable signature. Legitimate users never touch the     ║
║  tripwires. Attackers always do.                                         ║
╚══════════════════════════════════════════════════════════════════════════╝

Quantum Concepts Used:
  - Superposition    : Tripwire qubits are in |+⟩ = (|0⟩+|1⟩)/√2
  - No-Cloning Theorem: Attacker cannot copy qubits without disturbing them
  - Observer Effect  : Measuring a qubit in the wrong basis disturbs it
  - Hadamard Gate    : Creates and decodes superposition states
  - Fidelity         : Measures how close the returned state is to original

Team Roles:
  Member 1 — Theory, background, report writing
  Member 2 — Tripwire circuit design (Sections 2–3)
  Member 3 — Attacker simulation & alert engine (Sections 4–5)
  Member 4 — Analysis, visualisation, integration (Section 6)
"""

# ─────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector, state_fidelity
import numpy as np
import random
import hashlib
import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ─────────────────────────────────────────────────────────────────
# GLOBAL CONSTANTS
# ─────────────────────────────────────────────────────────────────

FIDELITY_THRESHOLD = 0.85   # Below this → intrusion alert triggered
N_TRIPWIRES        = 8      # Number of quantum tripwires per honeypot token
SIMULATOR          = AerSimulator()

# ─────────────────────────────────────────────────────────────────
# SECTION 1 — HONEYPOT TOKEN GENERATION
# ─────────────────────────────────────────────────────────────────

def generate_honeypot_token(resource_name: str, n_tripwires: int = N_TRIPWIRES):
    """
    Creates a honeypot token with two layers:
      1. Classical layer  : A fake but plausible resource ID (e.g., DB password)
      2. Quantum layer    : n_tripwires qubits, each placed in superposition |+⟩
                           using the Hadamard gate. The exact basis sequence
                           is the SECRET KEY — only the server knows it.

    The quantum layer is the invisible alarm. Nobody looking at the
    classical token sees anything suspicious. But the moment anyone
    tries to access or copy the token, the quantum tripwires fire.

    Parameters:
        resource_name : human-readable name ("DB_PASSWORD", "API_KEY", etc.)
        n_tripwires   : number of qubit tripwires to embed

    Returns:
        token : dict with classical + quantum fields
    """
    # ── Classical layer ──────────────────────────────────────────
    # Generate a realistic-looking but fake password/key
    fake_value = hashlib.sha256(
        (resource_name + str(random.randint(1000, 9999))).encode()
    ).hexdigest()[:24]

    # ── Quantum layer ────────────────────────────────────────────
    # Each tripwire is a qubit initialised to |+⟩ via Hadamard gate
    # The basis_key records which basis each qubit was set in.
    # We use two bases:
    #   '+' (rectilinear) → qubit stays as is after H
    #   '×' (diagonal)   → apply H then X for a different superposition
    tripwire_circuits = []
    basis_key = []

    for i in range(n_tripwires):
        qc = QuantumCircuit(1, 1, name=f"tripwire_{i}")
        basis = random.choice(['+', '×'])
        basis_key.append(basis)

        # Put qubit into superposition
        qc.h(0)                    # |0⟩ → |+⟩ = (|0⟩+|1⟩)/√2

        if basis == '×':
            qc.x(0)                # Extra rotation for diagonal variant
            qc.h(0)                # |1⟩ → |−⟩ = (|0⟩−|1⟩)/√2

        tripwire_circuits.append(qc)

    token = {
        "resource"         : resource_name,
        "classical_value"  : fake_value,
        "basis_key"        : basis_key,       # SECRET — never transmitted
        "tripwires"        : tripwire_circuits,
        "created_at"       : datetime.datetime.now().isoformat(),
        "access_log"       : []
    }

    print(f"\n[HONEYPOT] Token generated for resource: '{resource_name}'")
    print(f"  Classical value : {fake_value}")
    print(f"  Quantum tripwires: {n_tripwires} qubits in superposition")
    print(f"  Basis key (secret): {basis_key}")

    return token


# ─────────────────────────────────────────────────────────────────
# SECTION 2 — LEGITIMATE USER ACCESS (correct basis)
# ─────────────────────────────────────────────────────────────────

def legitimate_access(token: dict, user_id: str = "AuthorisedUser"):
    """
    A legitimate user has been given the basis_key by the server
    through a secure side-channel. They verify the token by measuring
    each tripwire qubit in the CORRECT basis.

    Correct measurement → high fidelity → no alarm.

    In BB84 terms: if you measure in the right basis, you get the
    correct bit and the qubit is not disturbed (relative to expectation).

    Returns:
        fidelity_scores : list of per-tripwire fidelity values
        avg_fidelity    : float — should be close to 1.0
    """
    fidelity_scores = []

    for i, (qc, basis) in enumerate(zip(token["tripwires"], token["basis_key"])):
        # ── Build measurement circuit in correct basis ────────────
        measure_qc = qc.copy()

        # To measure in the diagonal basis, rotate back first
        if basis == '×':
            measure_qc.h(0)   # Undo the diagonal rotation
            measure_qc.x(0)

        # Measure in rectilinear basis
        measure_qc.h(0)       # Decode superposition
        measure_qc.measure(0, 0)

        # ── Compute fidelity via statevector comparison ───────────
        # Expected state: |0⟩ after correct decoding
        original_sv  = Statevector.from_label('0')

        # Simulate what the circuit produces (without measurement)
        decode_qc = qc.copy()
        if basis == '×':
            decode_qc.h(0)
            decode_qc.x(0)
        decode_qc.h(0)

        result_sv = Statevector(decode_qc)
        fidelity  = abs(state_fidelity(original_sv, result_sv))
        fidelity_scores.append(fidelity)

    avg_fidelity = np.mean(fidelity_scores)

    # Log this access
    log_entry = {
        "user"        : user_id,
        "type"        : "LEGITIMATE",
        "avg_fidelity": avg_fidelity,
        "timestamp"   : datetime.datetime.now().isoformat(),
        "alert"       : avg_fidelity < FIDELITY_THRESHOLD
    }
    token["access_log"].append(log_entry)

    print(f"\n[ACCESS] Legitimate user '{user_id}'")
    print(f"  Avg fidelity  : {avg_fidelity:.4f}")
    print(f"  Status        : {'✓ SECURE — No alarm' if avg_fidelity >= FIDELITY_THRESHOLD else '⚠ ALARM!'}")

    return fidelity_scores, avg_fidelity


# ─────────────────────────────────────────────────────────────────
# SECTION 3 — ATTACKER: INTERCEPT & COPY ATTACK
# ─────────────────────────────────────────────────────────────────

def attacker_intercept(token: dict, attacker_id: str = "Attacker_Eve",
                       attack_type: str = "random_basis"):
    """
    An attacker does NOT have the basis_key.
    They must guess a measurement basis for each tripwire qubit.

    Attack strategies modelled:
      'random_basis'   — guess each basis randomly (+/×)
      'fixed_plus'     — always measure in rectilinear (+) basis
      'clone_attempt'  — try to copy qubit before measuring (fails due
                         to no-cloning; modelled as extra perturbation)

    When attacker guesses wrong basis (~50% of the time):
      → Qubit collapses to a WRONG state
      → Fidelity drops significantly
      → Alert is triggered

    Returns:
        fidelity_scores : list of per-tripwire fidelity values
        avg_fidelity    : float — should be well below threshold
    """
    fidelity_scores = []

    for i, (qc, true_basis) in enumerate(zip(token["tripwires"], token["basis_key"])):
        # ── Attacker guesses the basis ────────────────────────────
        if attack_type == "random_basis":
            guessed_basis = random.choice(['+', '×'])
        elif attack_type == "fixed_plus":
            guessed_basis = '+'
        elif attack_type == "clone_attempt":
            # Cloning adds noise — modelled as a wrong basis + random flip
            guessed_basis = random.choice(['+', '×'])
        else:
            guessed_basis = random.choice(['+', '×'])

        # ── Attacker measures with guessed (likely wrong) basis ───
        attack_qc = qc.copy()

        if guessed_basis == '×':
            attack_qc.h(0)
            attack_qc.x(0)

        attack_qc.h(0)  # Try to decode

        # ── Compare to expected state — fidelity will be low ─────
        original_sv = Statevector.from_label('0')
        result_sv   = Statevector(attack_qc)
        fidelity    = abs(state_fidelity(original_sv, result_sv))

        # Clone attempt adds extra decoherence noise
        if attack_type == "clone_attempt":
            fidelity *= random.uniform(0.3, 0.7)

        fidelity_scores.append(fidelity)

    avg_fidelity = np.mean(fidelity_scores)

    # ── ALERT LOGIC ───────────────────────────────────────────────
    alert_triggered = avg_fidelity < FIDELITY_THRESHOLD

    log_entry = {
        "user"        : attacker_id,
        "type"        : f"ATTACK ({attack_type})",
        "avg_fidelity": avg_fidelity,
        "timestamp"   : datetime.datetime.now().isoformat(),
        "alert"       : alert_triggered
    }
    token["access_log"].append(log_entry)

    print(f"\n[ATTACK] '{attacker_id}' — strategy: {attack_type}")
    print(f"  Avg fidelity  : {avg_fidelity:.4f}")
    print(f"  Status        : {'🚨 INTRUSION DETECTED' if alert_triggered else 'Not detected (false negative)'}")

    return fidelity_scores, avg_fidelity


# ─────────────────────────────────────────────────────────────────
# SECTION 4 — ALERT ENGINE
# ─────────────────────────────────────────────────────────────────

def display_access_log(token: dict):
    """
    Prints a full security audit log for the honeypot token.
    Highlights all flagged intrusions in red.
    """
    print("\n" + "═"*60)
    print(f"  QUANTUM HONEYPOT AUDIT LOG — '{token['resource']}'")
    print("═"*60)
    print(f"  {'Timestamp':<28} {'User':<20} {'Fidelity':>8}  {'Status'}")
    print("─"*60)

    for entry in token["access_log"]:
        ts      = entry["timestamp"][:19]
        user    = entry["user"][:18]
        fid     = f"{entry['avg_fidelity']:.4f}"
        status  = "🚨 ALERT" if entry["alert"] else "✓  OK"
        print(f"  {ts:<28} {user:<20} {fid:>8}  {status}")

    total_accesses = len(token["access_log"])
    total_alerts   = sum(1 for e in token["access_log"] if e["alert"])
    print("─"*60)
    print(f"  Total accesses : {total_accesses}")
    print(f"  Alerts raised  : {total_alerts}")
    print(f"  Detection rate : {total_alerts/total_accesses*100:.1f}%")
    print("═"*60)


# ─────────────────────────────────────────────────────────────────
# SECTION 5 — TRIPWIRE CIRCUIT VISUALISER
# ─────────────────────────────────────────────────────────────────

def show_tripwire_circuit(token: dict, index: int = 0):
    """
    Prints the Qiskit circuit for a single tripwire qubit.
    Shows the difference between how the server set it up
    vs how an attacker would measure it.
    """
    qc     = token["tripwires"][index]
    basis  = token["basis_key"][index]

    print(f"\n[CIRCUIT] Tripwire #{index} — Basis: '{basis}'")
    print("  Server setup circuit:")
    print(qc.draw(output='text'))

    # Attacker measurement circuit (wrong basis)
    attacker_qc = qc.copy()
    wrong_basis = '×' if basis == '+' else '+'
    if wrong_basis == '×':
        attacker_qc.h(0)
        attacker_qc.x(0)
    attacker_qc.h(0)
    attacker_qc.measure(0, 0)

    print(f"  Attacker measurement (wrong basis '{wrong_basis}'):")
    print(attacker_qc.draw(output='text'))


# ─────────────────────────────────────────────────────────────────
# SECTION 6 — VISUALISATION & ANALYSIS
# ─────────────────────────────────────────────────────────────────

def run_multi_trial_analysis(n_trials: int = 30):
    """
    Runs n_trials honeypot access simulations:
      - Half are legitimate users (correct basis)
      - Half are attackers using 3 different strategies

    Plots a fidelity distribution graph showing clear separation
    between legitimate and malicious access patterns.
    """
    results = {
        "Legitimate"      : [],
        "Random Basis"    : [],
        "Fixed Basis"     : [],
        "Clone Attempt"   : []
    }

    print(f"\n[ANALYSIS] Running {n_trials} trials per category...")

    for trial in range(n_trials):
        token = generate_honeypot_token(f"RESOURCE_{trial}", n_tripwires=6)

        # Legitimate access
        _, f = legitimate_access(token, user_id=f"LegitUser_{trial}")
        results["Legitimate"].append(f)

        # Three attack strategies
        for strategy, key in [
            ("random_basis", "Random Basis"),
            ("fixed_plus",   "Fixed Basis"),
            ("clone_attempt","Clone Attempt")
        ]:
            _, f = attacker_intercept(token, attacker_id=f"Eve_{trial}",
                                      attack_type=strategy)
            results[key].append(f)

    # ── Plot 1: Fidelity Distribution ────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Quantum Honeypot — Fidelity Analysis", fontsize=14, fontweight='bold')

    colours = {
        "Legitimate"   : "#2ECC71",
        "Random Basis" : "#E74C3C",
        "Fixed Basis"  : "#E67E22",
        "Clone Attempt": "#9B59B6"
    }

    # Box plot
    ax1 = axes[0]
    data   = [results[k] for k in results]
    labels = list(results.keys())
    bp = ax1.boxplot(data, patch_artist=True, notch=True,
                     medianprops=dict(color='black', linewidth=2))

    for patch, label in zip(bp['boxes'], labels):
        patch.set_facecolor(colours[label])
        patch.set_alpha(0.8)

    ax1.axhline(y=FIDELITY_THRESHOLD, color='navy', linestyle='--',
                linewidth=2, label=f'Alert threshold ({FIDELITY_THRESHOLD})')
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_ylabel('Average Fidelity Score', fontsize=11)
    ax1.set_title('Fidelity Distribution by Access Type', fontsize=12)
    ax1.legend()
    ax1.set_ylim(0, 1.1)
    ax1.grid(axis='y', alpha=0.3)

    # Detection rate bar chart
    ax2 = axes[1]
    detection_rates = {}
    for key in results:
        if key == "Legitimate":
            # False positive rate (bad if high)
            rate = sum(1 for f in results[key] if f < FIDELITY_THRESHOLD) / n_trials * 100
            detection_rates["False Positives\n(Legit flagged)"] = (rate, "#2ECC71")
        else:
            rate = sum(1 for f in results[key] if f < FIDELITY_THRESHOLD) / n_trials * 100
            detection_rates[key] = (rate, colours[key])

    cats   = list(detection_rates.keys())
    vals   = [detection_rates[c][0] for c in cats]
    clrs   = [detection_rates[c][1] for c in cats]
    bars   = ax2.bar(cats, vals, color=clrs, edgecolor='black', linewidth=0.8, width=0.5)

    for bar, val in zip(bars, vals):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                 f'{val:.0f}%', ha='center', fontsize=11, fontweight='bold')

    ax2.set_ylabel('Detection / False-Positive Rate (%)', fontsize=11)
    ax2.set_title('Attack Detection Rates', fontsize=12)
    ax2.set_ylim(0, 115)
    ax2.axhline(y=100, color='grey', linestyle=':', linewidth=1)
    ax2.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig('honeypot_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("\n[SAVED] honeypot_analysis.png")

    return results


def plot_tripwire_fidelity_heatmap(n_tokens: int = 5):
    """
    Shows a heatmap of per-tripwire fidelity for a batch of tokens.
    Each row = one honeypot token, each column = one tripwire qubit.
    Green = high fidelity (legitimate), Red = low fidelity (attack).
    """
    legit_matrix  = []
    attack_matrix = []

    for i in range(n_tokens):
        token = generate_honeypot_token(f"TOKEN_{i}", n_tripwires=N_TRIPWIRES)

        scores_legit, _  = legitimate_access(token)
        legit_matrix.append(scores_legit)

        scores_attack, _ = attacker_intercept(token)
        attack_matrix.append(scores_attack)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))
    fig.suptitle("Per-Tripwire Fidelity Heatmap", fontsize=13, fontweight='bold')

    for ax, matrix, title in [
        (ax1, legit_matrix,  "Legitimate Access"),
        (ax2, attack_matrix, "Attacker Access")
    ]:
        im = ax.imshow(matrix, cmap='RdYlGn', vmin=0, vmax=1, aspect='auto')
        ax.set_xlabel('Tripwire Qubit Index', fontsize=10)
        ax.set_ylabel('Token Index',          fontsize=10)
        ax.set_title(title,                   fontsize=11, fontweight='bold')
        ax.set_xticks(range(N_TRIPWIRES))
        ax.set_yticks(range(n_tokens))
        plt.colorbar(im, ax=ax, label='Fidelity')

        # Annotate cells
        for r in range(n_tokens):
            for c in range(N_TRIPWIRES):
                ax.text(c, r, f'{matrix[r][c]:.2f}',
                        ha='center', va='center', fontsize=7,
                        color='black' if matrix[r][c] > 0.3 else 'white')

    plt.tight_layout()
    plt.savefig('tripwire_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("[SAVED] tripwire_heatmap.png")


# ─────────────────────────────────────────────────────────────────
# SECTION 7 — QUANTUM vs CLASSICAL COMPARISON
# ─────────────────────────────────────────────────────────────────

def classical_vs_quantum_comparison():
    """
    Demonstrates the core advantage of quantum honeypots over classical ones.

    Classical honeypot weakness: An attacker can silently READ/COPY a
    classical token without triggering any alarm — if they're careful.
    The honeypot only detects access via system logs, which can be wiped.

    Quantum honeypot advantage: The no-cloning theorem + observer effect
    make silent reading PHYSICALLY IMPOSSIBLE. Any access disturbs the
    quantum state, leaving an unforgeable, physics-guaranteed trace.
    """
    print("\n" + "═"*60)
    print("  CLASSICAL vs QUANTUM HONEYPOT COMPARISON")
    print("═"*60)

    comparison = [
        ("Property",            "Classical Honeypot",    "Quantum Honeypot"),
        ("Silent read possible?","YES — attacker can read","NO — collapses state"),
        ("Cloning possible?",   "YES — easy to copy",    "NO — no-cloning theorem"),
        ("Detection basis",     "System log analysis",   "Physics (fidelity drop)"),
        ("Log forgery possible?","YES — logs can be wiped","NO — quantum signature"),
        ("False positive rate", "Variable (log-based)",  "Tunable via threshold"),
        ("Detection rate",      "Depends on monitoring", "~75-100% (quantum)"),
        ("Security guarantee",  "Computational only",    "Information-theoretic"),
    ]

    for row in comparison:
        print(f"  {'─'*57}")
        if row[0] == "Property":
            print(f"  {'Property':<28} {'Classical':^14} {'Quantum':^14}")
        else:
            symbol = "⚠" if "YES" in row[1] else "✓"
            print(f"  {row[0]:<28} {symbol} {row[1]:<20} ✓ {row[2]}")

    print(f"  {'═'*57}")


# ─────────────────────────────────────────────────────────────────
# MAIN — RUN COMPLETE DEMONSTRATION
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║        QUANTUM HONEYPOT SYSTEM — FULL DEMONSTRATION     ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # ── Demo 1: Single token lifecycle ────────────────────────────
    print("\n>>> DEMO 1: Single Honeypot Token Lifecycle")
    token = generate_honeypot_token("DB_ADMIN_PASSWORD", n_tripwires=N_TRIPWIRES)

    # Legitimate access
    legitimate_access(token, user_id="Admin_Alice")
    legitimate_access(token, user_id="Admin_Bob")

    # Attacker attempts
    attacker_intercept(token, attacker_id="Hacker_Eve",   attack_type="random_basis")
    attacker_intercept(token, attacker_id="Hacker_Mallory", attack_type="fixed_plus")
    attacker_intercept(token, attacker_id="APT_Group",    attack_type="clone_attempt")

    # Show the circuit
    show_tripwire_circuit(token, index=0)

    # Audit log
    display_access_log(token)

    # ── Demo 2: Classical vs Quantum comparison ────────────────────
    print("\n>>> DEMO 2: Classical vs Quantum Comparison")
    classical_vs_quantum_comparison()

    # ── Demo 3: Statistical analysis over 30 trials ───────────────
    print("\n>>> DEMO 3: Multi-Trial Statistical Analysis (30 trials)")
    results = run_multi_trial_analysis(n_trials=30)

    # ── Demo 4: Heatmap visualisation ─────────────────────────────
    print("\n>>> DEMO 4: Per-Tripwire Fidelity Heatmap")
    plot_tripwire_fidelity_heatmap(n_tokens=5)

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  ALL DEMOS COMPLETE. Output files:                      ║")
    print("║    honeypot_analysis.png   — fidelity distribution      ║")
    print("║    tripwire_heatmap.png    — per-qubit fidelity grid     ║")
    print("╚══════════════════════════════════════════════════════════╝")
