"""Quantum Honeypot Statistical Analytics, Monte-Carlo Experiments, and Chart Generation."""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from ..tokens.generator import generate_honeytoken
from ..tokens.verifier import verify_token_access
from ..core.bell_chsh import calculate_chsh_correlations

def run_quantum_benchmark(n_trials: int = 50, n_qubits: int = 8, noise_floor: float = 0.02) -> dict:
    """Run comprehensive Monte-Carlo benchmark across all quantum attack vectors."""
    categories = [
        "Legitimate",
        "Random Intercept",
        "Fixed Basis",
        "UQCM Cloning",
        "Asymm Cloner"
    ]
    strat_map = {
        "Legitimate": "legit",
        "Random Intercept": "random",
        "Fixed Basis": "fixed_basis",
        "UQCM Cloning": "cloning_uqcm",
        "Asymm Cloner": "asymmetric_clone"
    }

    results = {cat: [] for cat in categories}
    chsh_scores = {"Intact Bell Pair": [], "Intercepted Bell Pair": []}

    for _ in range(n_trials):
        token = generate_honeytoken("api_key", "Benchmark Token", n_qubits=n_qubits, enable_entanglement=True)
        for cat, strat in strat_map.items():
            res = verify_token_access(token, strategy=strat, channel_noise=noise_floor)
            results[cat].append(res.mean_fidelity)

        # CHSH runs
        c_clean = calculate_chsh_correlations(noise_p=noise_floor, intercepted=False)
        c_attack = calculate_chsh_correlations(noise_p=noise_floor, intercepted=True)
        chsh_scores["Intact Bell Pair"].append(c_clean["S"])
        chsh_scores["Intercepted Bell Pair"].append(c_attack["S"])

    return {"fidelities": results, "chsh": chsh_scores, "n_trials": n_trials, "noise": noise_floor}

def generate_analytics_charts(benchmark_data: dict, output_dir: str = "charts") -> dict:
    """Generate high-resolution comparative visualization charts."""
    os.makedirs(output_dir, exist_ok=True)
    results = benchmark_data["fidelities"]
    chsh_data = benchmark_data["chsh"]
    n = benchmark_data["n_trials"]
    threshold = 0.85

    labels = list(results.keys())
    colors = ['#10B981', '#EF4444', '#F59E0B', '#8B5CF6', '#EC4899']
    means = [np.mean(results[k]) for k in labels]
    stds = [np.std(results[k]) for k in labels]
    rates = [sum(1 for f in results[k] if f < threshold) / n * 100 for k in labels]

    chart_paths = {}

    # 1. Fidelity Comparison Bar Chart
    plt.figure(figsize=(8, 4.5), dpi=150)
    bars = plt.bar(labels, means, yerr=stds, capsize=5, color=colors, edgecolor='#1E293B', linewidth=1.2)
    plt.axhline(threshold, color='#DC2626', linestyle='--', linewidth=2, label=f'Alert Threshold ({threshold})')
    plt.title(f'Quantum Honeypot: Average State Fidelity (n={n} trials, 8 qubits)', fontsize=12, fontweight='bold', pad=12)
    plt.ylabel('Fidelity Score F(rho, psi)', fontsize=10)
    plt.ylim(0, 1.15)
    for bar, val in zip(bars, means):
        plt.text(bar.get_x() + bar.get_width() / 2, val + 0.03, f"{val:.3f}", ha='center', fontsize=9, fontweight='bold')
    plt.legend(loc='lower right')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    p1 = os.path.join(output_dir, "chart_fidelity.png")
    plt.savefig(p1)
    plt.close()
    chart_paths["fidelity"] = p1

    # 2. Detection Rate Bar Chart
    plt.figure(figsize=(8, 4.5), dpi=150)
    det_bars = plt.bar(labels, rates, color=colors, edgecolor='#1E293B', linewidth=1.2)
    plt.title(f'Intrusion Detection Rate & False Alarm Rate (n={n})', fontsize=12, fontweight='bold', pad=12)
    plt.ylabel('Detection Rate (%)', fontsize=10)
    plt.ylim(0, 115)
    for bar, val in zip(det_bars, rates):
        plt.text(bar.get_x() + bar.get_width() / 2, val + 2, f"{val:.1f}%", ha='center', fontsize=9, fontweight='bold')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    p2 = os.path.join(output_dir, "chart_detection.png")
    plt.savefig(p2)
    plt.close()
    chart_paths["detection"] = p2

    # 3. Distribution Box Plot
    plt.figure(figsize=(8, 4.5), dpi=150)
    bp = plt.boxplot([results[k] for k in labels], patch_artist=True, tick_labels=labels, medianprops=dict(color='black', linewidth=2))
    for patch, c in zip(bp['boxes'], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.7)
    plt.axhline(threshold, color='#DC2626', linestyle='--', linewidth=2, label='Alert Threshold')
    plt.title('Fidelity Distribution & Interquartile Spread', fontsize=12, fontweight='bold', pad=12)
    plt.ylabel('Fidelity Score', fontsize=10)
    plt.legend(loc='lower right')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    p3 = os.path.join(output_dir, "chart_boxplot.png")
    plt.savefig(p3)
    plt.close()
    chart_paths["boxplot"] = p3

    # 4. CHSH Bell Parameter Violation Chart
    plt.figure(figsize=(7, 4.5), dpi=150)
    chsh_labels = ["Intact Entanglement", "Eavesdropped / Collapsed"]
    chsh_means = [np.mean(chsh_data["Intact Bell Pair"]), np.mean(chsh_data["Intercepted Bell Pair"])]
    chsh_stds = [np.std(chsh_data["Intact Bell Pair"]), np.std(chsh_data["Intercepted Bell Pair"])]
    chsh_colors = ['#10B981', '#EF4444']
    
    cbars = plt.bar(chsh_labels, chsh_means, yerr=chsh_stds, capsize=6, color=chsh_colors, edgecolor='#1E293B', width=0.45)
    plt.axhline(2.0, color='navy', linestyle='--', linewidth=2, label='Classical Limit S <= 2.0 (Bell Inequality)')
    plt.axhline(2.828, color='purple', linestyle=':', linewidth=2, label='Tsirelson Bound S = 2*sqrt(2) ~ 2.828')
    plt.title('Entangled Canary Tripwire: CHSH Bell Parameter (S)', fontsize=12, fontweight='bold', pad=12)
    plt.ylabel('Bell Parameter S', fontsize=10)
    plt.ylim(0, 3.4)
    for bar, val in zip(cbars, chsh_means):
        plt.text(bar.get_x() + bar.get_width() / 2, val + 0.08, f"S = {val:.3f}", ha='center', fontsize=10, fontweight='bold')
    plt.legend(loc='lower left', fontsize=8.5)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    p4 = os.path.join(output_dir, "chart_chsh.png")
    plt.savefig(p4)
    plt.close()
    chart_paths["chsh"] = p4

    # 5. Per-trial Line Plot
    plt.figure(figsize=(9, 4.5), dpi=150)
    x = range(1, n + 1)
    for label, c in zip(labels, colors):
        plt.plot(x, results[label], color=c, alpha=0.8, linewidth=1.4, label=label)
    plt.axhline(threshold, color='black', linestyle='--', linewidth=1.8, label=f'Threshold ({threshold})')
    plt.fill_between(x, 0, threshold, alpha=0.08, color='red', label='Intrusion Zone')
    plt.title('Per-Trial Trajectory Across Quantum Attack Vectors', fontsize=12, fontweight='bold', pad=12)
    plt.xlabel('Trial Index', fontsize=10)
    plt.ylabel('Fidelity Score', fontsize=10)
    plt.ylim(0.2, 1.05)
    plt.legend(loc='lower right', fontsize=8)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    p5 = os.path.join(output_dir, "chart_trials.png")
    plt.savefig(p5)
    plt.close()
    chart_paths["trials"] = p5

    return chart_paths
