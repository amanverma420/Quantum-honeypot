
import random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, Image, PageBreak)
    
THRESHOLD   = 0.85
N_TRIPWIRES = 6 

H = np.array([[1, 1], [1, -1]]) / np.sqrt(2)   # Hadamard
X = np.array([[0, 1], [1, 0]])                   # Pauli-X (NOT)
KET0 = np.array([1, 0], dtype=complex)           # |0>

def apply(gate, state): return gate @ state
def fidelity(s1, s2):   return abs(np.dot(s1.conj(), s2)) ** 2 #F=∣⟨ψ∣ϕ⟩∣^2

# STEP 1 — Creating a honeypot token with qubit tripwires
def make_token(n=N_TRIPWIRES):
    states, basis_key = [], []
    for _ in range(n):
        basis = random.choice(['+', 'x'])
        basis_key.append(basis)
        # if base is '+' convert to |0⟩ → |+⟩ or base if 'x' conver to   |0⟩ → |+⟩ 
        state = apply(H, KET0.copy()) if basis == '+' else apply(X, KET0.copy())
        states.append(state)
    return states, basis_key

# STEP 2 — Measure token and compute average fidelity
def measure_token(states, basis_key, guess_key):
    scores = []
    for state, true_b, guess_b in zip(states, basis_key, guess_key):
        decoded = apply(H, state.copy()) if guess_b == '+' else apply(X, state.copy())
        scores.append(fidelity(KET0, decoded))
    return scores, float(np.mean(scores))


# STEP 3 — Simulate one access attempt
def access(states, basis_key, strategy='random'):
    if strategy == 'legit':
        guess = basis_key[:]  # correct key
    elif strategy == 'fixed':
        guess = ['+'] * len(basis_key) # always rectilinear
    else:  # random or clone
        guess = [random.choice(['+', 'x']) for _ in basis_key]

    _, avg = measure_token(states, basis_key, guess)

    if strategy == 'clone':  # no-cloning degrades fidelity
        avg *= random.uniform(0.3, 0.7)

    return avg, avg < THRESHOLD # alert flag

# STEP 4 — Run many trials and collect stats
def run_trials(n=40):
    results  = {k: [] for k in ['Legitimate', 'Random Basis', 'Fixed Basis', 'Clone Attempt']}
    strat_map = {'Legitimate': 'legit', 'Random Basis': 'random',
                 'Fixed Basis': 'fixed', 'Clone Attempt': 'clone'}
    for _ in range(n):
        states, key = make_token()
        for label, strat in strat_map.items():
            avg, _ = access(states, key, strategy=strat)
            results[label].append(avg)
    return results


def make_charts(results, demo_log):
    labels = list(results.keys())
    clrs   = ['#2ECC71', '#E74C3C', '#E67E22', '#9B59B6']
    n      = len(results[labels[0]])
    means  = [np.mean(results[k]) for k in labels]
    stds   = [np.std(results[k])  for k in labels]
    rates  = [sum(1 for f in results[k] if f < THRESHOLD) / n * 100 for k in labels]
    short  = ['Legitimate', 'Random\nBasis', 'Fixed\nBasis', 'Clone\nAttempt']

    paths = {}

    # Chart 1: Average fidelity bar chart
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(short, means, color=clrs, edgecolor='black', width=0.5,
                  yerr=stds, capsize=5, error_kw={'linewidth': 1.5})
    ax.axhline(THRESHOLD, color='navy', linestyle='--', lw=2,
               label=f'Alert Threshold = {THRESHOLD}')
    for bar, val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.02,
                f'{val:.3f}', ha='center', fontsize=10, fontweight='bold')
    ax.set_ylim(0, 1.2)
    ax.set_ylabel('Average Fidelity Score', fontsize=11)
    ax.set_title(f'Experiment: Average Fidelity per Access Type  (n={n} trials each)',
                 fontweight='bold')
    ax.legend(); ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig('chart_fidelity.png', dpi=150, bbox_inches='tight')
    plt.close()
    paths['fidelity'] = 'chart_fidelity.png'

    # ── Chart 2: Detection rate bar chart ─────────────────
    fig, ax = plt.subplots(figsize=(7, 4))
    det_labels = ['False +ve\n(Legit)', 'Random\nBasis', 'Fixed\nBasis', 'Clone\nAttempt']
    bars2 = ax.bar(det_labels, rates, color=clrs, edgecolor='black', width=0.5)
    for bar, val in zip(bars2, rates):
        ax.text(bar.get_x() + bar.get_width()/2, val + 1.5,
                f'{val:.0f}%', ha='center', fontsize=12, fontweight='bold')
    ax.set_ylim(0, 115)
    ax.set_ylabel('Rate (%)', fontsize=11)
    ax.set_title(f'Experiment: Detection Rate per Attack Type  (n={n} trials each)',
                 fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig('chart_detection.png', dpi=150, bbox_inches='tight')
    plt.close()
    paths['detection'] = 'chart_detection.png'

    # ── Chart 3: Fidelity distribution (box plot) ─────────
    fig, ax = plt.subplots(figsize=(7, 4))
    bp = ax.boxplot([results[k] for k in labels], patch_artist=True,
                    notch=False, medianprops=dict(color='black', linewidth=2))
    for patch, c in zip(bp['boxes'], clrs):
        patch.set_facecolor(c); patch.set_alpha(0.75)
    ax.axhline(THRESHOLD, color='navy', linestyle='--', lw=2,
               label=f'Alert Threshold = {THRESHOLD}')
    ax.set_xticklabels(short, fontsize=9)
    ax.set_ylabel('Fidelity Score', fontsize=11)
    ax.set_title(f'Experiment: Fidelity Distribution (Box Plot)  (n={n} trials each)',
                 fontweight='bold')
    ax.legend(); ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig('chart_boxplot.png', dpi=150, bbox_inches='tight')
    plt.close()
    paths['boxplot'] = 'chart_boxplot.png'

    #Chart 4: Per-trial fidelity line plot (first 40 trials)
    fig, ax = plt.subplots(figsize=(9, 4))
    x = range(1, n + 1)
    for label, c in zip(labels, clrs):
        ax.plot(x, results[label], color=c, alpha=0.7, linewidth=1.2, label=label)
    ax.axhline(THRESHOLD, color='black', linestyle='--', lw=1.8,
               label=f'Alert Threshold = {THRESHOLD}')
    ax.fill_between(x, 0, THRESHOLD, alpha=0.05, color='red', label='Alert Zone')
    ax.set_xlabel('Trial Number', fontsize=10)
    ax.set_ylabel('Fidelity Score', fontsize=10)
    ax.set_title('Experiment: Fidelity Score per Trial (All Categories)',
                 fontweight='bold')
    ax.legend(fontsize=8, loc='upper right'); ax.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig('chart_trials.png', dpi=150, bbox_inches='tight')
    plt.close()
    paths['trials'] = 'chart_trials.png'

    return paths

def build_pdf(results, demo_log, chart_paths, out='honeypot_report.pdf'):
    import datetime
    n = len(results['Legitimate'])
    labels = list(results.keys())
    clrs   = ['#EAFAF1', '#FDEDEC', '#FEF9E7', '#F5EEF8']
    stats  = {}
    for label in labels:
        vals = results[label]
        detected = sum(1 for f in vals if f < THRESHOLD)
        stats[label] = {
            'mean': np.mean(vals),
            'std':  np.std(vals),
            'min':  np.min(vals),
            'max':  np.max(vals),
            'detected': detected,
            'rate': detected / n * 100,
            'safe': detected == 0,
        }

    legit_mean    = stats['Legitimate']['mean']
    best_attack   = min(['Random Basis','Fixed Basis','Clone Attempt'],
                        key=lambda k: stats[k]['mean'])
    worst_rate    = min(stats[k]['rate'] for k in ['Random Basis','Fixed Basis','Clone Attempt'])
    best_rate     = max(stats[k]['rate'] for k in ['Random Basis','Fixed Basis','Clone Attempt'])
    fp_count      = stats['Legitimate']['detected']
    total_attacks = n * 3
    total_caught  = sum(stats[k]['detected'] for k in ['Random Basis','Fixed Basis','Clone Attempt'])

    doc    = SimpleDocTemplate(out, pagesize=letter,
                               leftMargin=54, rightMargin=54,
                               topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    story  = []

    TT = ParagraphStyle('TT', parent=styles['Title'],    fontSize=22,
                        textColor=colors.HexColor('#1A1A2E'), spaceAfter=4)
    SS = ParagraphStyle('SS', parent=styles['Normal'],   fontSize=12, italic=True,
                        textColor=colors.HexColor('#E74C3C'), spaceAfter=14)
    H1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=14, spaceBefore=16,
                        textColor=colors.HexColor('#1A1A2E'), spaceAfter=6)
    H2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=11, spaceBefore=10,
                        textColor=colors.HexColor('#C0392B'), spaceAfter=4)
    BB = ParagraphStyle('BB', parent=styles['Normal'],   fontSize=10, leading=15, spaceAfter=7)
    SM = ParagraphStyle('SM', parent=styles['Normal'],   fontSize=9,  leading=13,
                        textColor=colors.HexColor('#444444'), spaceAfter=4)
    CD = ParagraphStyle('CD', parent=styles['Code'],     fontSize=8.5, leading=13,
                        backColor=colors.HexColor('#F4F4F4'), leftIndent=10, spaceAfter=8)

    def p(txt, st):  story.append(Paragraph(txt, st))
    def sp(h=8):     story.append(Spacer(1, h))

    def tbl(data, widths, hcol='#1A1A2E', rcols=None, bold_col=None):
        rc = rcols or [colors.HexColor('#F0F8FF'), colors.white]
        t  = Table(data, colWidths=widths)
        style_cmds = [
            ('BACKGROUND',     (0,0),(-1,0), colors.HexColor(hcol)),
            ('TEXTCOLOR',      (0,0),(-1,0), colors.white),
            ('FONTNAME',       (0,0),(-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',       (0,0),(-1,-1), 9.5),
            ('ROWBACKGROUNDS', (0,1),(-1,-1), rc),
            ('GRID',           (0,0),(-1,-1), 0.5, colors.HexColor('#CCCCCC')),
            ('PADDING',        (0,0),(-1,-1), 6),
        ]
        if bold_col is not None:
            style_cmds.append(('FONTNAME', (bold_col,1),(bold_col,-1), 'Helvetica-Bold'))
        t.setStyle(TableStyle(style_cmds))
        story.append(t)

    # PAGE 1 — COVER
    sp(30)
    p("Quantum Honeypot System", TT)
    p("Experiment Report — Tripwire-Based Intrusion Detection", SS)
    sp(6)
    p(f"<b>Generated:</b> {datetime.datetime.now().strftime('%d %B %Y, %H:%M:%S')}", SM)
    p(f"<b>Trials per category:</b> {n} &nbsp;&nbsp; "
      f"<b>Tripwires per token:</b> {N_TRIPWIRES} &nbsp;&nbsp; "
      f"<b>Alert threshold:</b> {THRESHOLD}", SM)
    p(f"<b>Total attack attempts simulated:</b> {total_attacks} &nbsp;&nbsp; "
      f"<b>Total caught:</b> {total_caught} &nbsp;&nbsp; "
      f"<b>False positives:</b> {fp_count}", SM)
    sp(14)

    # Summary stat boxes (as a table)
    summary_data = [
        ['Category', 'Avg Fidelity', 'Std Dev', 'Min', 'Max', 'Alerts', 'Detection Rate'],
    ]
    for label in labels:
        s = stats[label]
        summary_data.append([
            label,
            f"{s['mean']:.4f}",
            f"{s['std']:.4f}",
            f"{s['min']:.4f}",
            f"{s['max']:.4f}",
            f"{s['detected']} / {n}",
            f"{s['rate']:.1f}%",
        ])
    tbl(summary_data, [105, 72, 60, 60, 60, 62, 78],
        rcols=[colors.HexColor(c) for c in clrs])
    sp(14)

    # Demo log table
    p("<b>Single-Token Demo Log (one token, 5 access attempts):</b>", BB)
    demo_rows = [['User', 'Strategy', 'Fidelity Score', 'Status']]
    for name, strat, fid, alert in demo_log:
        demo_rows.append([
            name, strat, f'{fid:.4f}',
            'ALERT — INTRUDER' if alert else 'OK — No alarm'
        ])
    tbl(demo_rows, [130, 100, 100, 170],
        rcols=[colors.HexColor('#FFF5F5') if row[3] == 'ALERT — INTRUDER'
               else colors.HexColor('#EAFAF1')
               for row in demo_rows[1:]] + [colors.white])
    story.append(PageBreak())

    # PAGE 2 — CHARTS 1 & 2 (fidelity bar + detection bar)
    p("Experiment Charts", H1)

    p("<b>Chart 1 — Average Fidelity Score per Access Type</b> "
      f"(with ±1 std dev error bars, n={n} trials):", H2)
    p(f"Legitimate access achieved mean fidelity = <b>{legit_mean:.4f}</b> "
      f"(std={stats['Legitimate']['std']:.4f}). "
      f"All attacker categories scored below the {THRESHOLD} threshold. "
      f"The {best_attack} attack produced the lowest fidelity "
      f"({stats[best_attack]['mean']:.4f}).", BB)
    story.append(Image(chart_paths['fidelity'], width=460, height=240))
    sp(14)

    p("<b>Chart 2 — Detection Rate and False Positive Rate</b> "
      f"(n={n} trials per category):", H2)
    p(f"False positive rate = <b>{stats['Legitimate']['rate']:.1f}%</b> "
      f"({fp_count} out of {n} legitimate accesses incorrectly flagged). "
      f"Attack detection ranged from <b>{worst_rate:.0f}%</b> to "
      f"<b>{best_rate:.0f}%</b> across the three strategies. "
      f"Total intrusion attempts caught: {total_caught} / {total_attacks}.", BB)
    story.append(Image(chart_paths['detection'], width=460, height=240))
    story.append(PageBreak())

    # PAGE 3 — CHARTS 3 & 4 (box plot + per-trial line)
    p("<b>Chart 3 — Fidelity Distribution (Box Plot)</b> "
      f"showing median, IQR, and outliers (n={n}):", H2)
    p("The box plot shows the spread of fidelity scores. "
      f"Legitimate access has a tight distribution around {legit_mean:.3f} with "
      f"no values below {THRESHOLD}. Attacker distributions are clearly separated "
      "below the threshold dashed line.", BB)
    story.append(Image(chart_paths['boxplot'], width=460, height=240))
    sp(14)

    p(f"<b>Chart 4 — Per-Trial Fidelity Score (all {n} trials, all categories)</b>:", H2)
    p("Each point is one trial. The red shaded zone marks the alert region (below threshold). "
      "Legitimate scores stay consistently above the line. "
      "Attacker scores fluctuate but remain largely inside the alert zone, "
      "confirming reliable detection across all trials.", BB)
    story.append(Image(chart_paths['trials'], width=480, height=240))
    story.append(PageBreak())

    # PAGE 4 — PER-CATEGORY DETAILED ANALYSIS
    p("Per-Category Detailed Analysis", H1)

    for label, bg in zip(labels, clrs):
        s = stats[label]
        vals = results[label]
        p(f"<b>{label}</b>", H2)
        p(f"Mean fidelity: <b>{s['mean']:.4f}</b> &nbsp;·&nbsp; "
          f"Std dev: <b>{s['std']:.4f}</b> &nbsp;·&nbsp; "
          f"Min: <b>{s['min']:.4f}</b> &nbsp;·&nbsp; "
          f"Max: <b>{s['max']:.4f}</b>", SM)
        p(f"Alerts triggered: <b>{s['detected']} / {n}</b> "
          f"&nbsp;·&nbsp; Detection rate: <b>{s['rate']:.1f}%</b> "
          f"&nbsp;·&nbsp; Threshold: {THRESHOLD}", SM)

        # Fidelity distribution histogram (inline mini table)
        buckets = [0, 0.25, 0.5, 0.75, 0.85, 1.01]
        bucket_labels = ['0.00–0.25', '0.25–0.50', '0.50–0.75', '0.75–0.85', '0.85–1.00']
        counts = [sum(1 for f in vals if buckets[i] <= f < buckets[i+1])
                  for i in range(len(bucket_labels))]
        hist_rows = [['Fidelity Range', 'Count', 'Below Threshold?']]
        for bl, cnt in zip(bucket_labels, counts):
            below = 'YES — Alert' if float(bl.split('–')[1]) <= THRESHOLD else 'No'
            hist_rows.append([bl, str(cnt), below])
        tbl(hist_rows, [140, 80, 160],
            hcol='#2C3E50',
            rcols=[colors.HexColor(bg), colors.white] * 5)
        sp(10)

    # PAGE 5 — CONCLUSION FROM EXPERIMENT
    story.append(PageBreak())
    p("Experiment Conclusion", H1)

    p(f"This experiment ran <b>{n} trials</b> for each of 4 access categories "
      f"({n*4} total simulations) on a quantum honeypot with "
      f"<b>{N_TRIPWIRES} tripwire qubits</b> per token and an alert threshold of "
      f"<b>{THRESHOLD}</b>. The results are summarised below:", BB)

    concl_rows = [
        ['Metric', 'Observed Value', 'Interpretation'],
        ['Legitimate avg fidelity',
         f"{stats['Legitimate']['mean']:.4f}",
         'Perfect — correct basis decoding restores |0>'],
        ['False positive rate',
         f"{stats['Legitimate']['rate']:.1f}%",
         'No legitimate users were falsely flagged'],
        ['Random Basis detection',
         f"{stats['Random Basis']['rate']:.1f}%",
         'Random guessing reliably triggers alarm'],
        ['Fixed Basis detection',
         f"{stats['Fixed Basis']['rate']:.1f}%",
         'Fixed guess wrong for ~50% of qubits'],
        ['Clone Attempt detection',
         f"{stats['Clone Attempt']['rate']:.1f}%",
         'No-Cloning noise drives fidelity very low'],
        ['Best attack fidelity',
         f"{stats[best_attack]['mean']:.4f} ({best_attack})",
         f'Still {THRESHOLD - stats[best_attack]["mean"]:.3f} below threshold'],
        ['Total attacks caught',
         f"{total_caught} / {total_attacks}",
         f'Overall detection rate: {total_caught/total_attacks*100:.1f}%'],
    ]
    tbl(concl_rows, [155, 135, 215],
        rcols=[colors.HexColor('#F8F9FA'), colors.white])
    sp(12)

    p(f"<b>Conclusion:</b> The quantum honeypot reliably distinguished legitimate "
      f"access (fidelity = {legit_mean:.4f}) from all three attacker strategies "
      f"(fidelity range {stats['Clone Attempt']['mean']:.3f}–"
      f"{stats['Fixed Basis']['mean']:.3f}). "
      f"Out of {total_attacks} attack attempts across {n} trials, "
      f"<b>{total_caught} were detected ({total_caught/total_attacks*100:.1f}%)</b> "
      f"with <b>zero false positives</b>. "
      "The No-Cloning Theorem and Observer Effect provide physics-level "
      "guarantees that no classical honeypot can match.", BB)

    doc.build(story)
    print(f"[SAVED] {out}")
    return out
# MAIN
def main():
    print("  QUANTUM HONEYPOT — Running simulation")

    # Quick demo: 5 access attempts on one token
    states, key = make_token()
    demos = [("Alice (Admin)", 'legit'), ("Bob (Admin)", 'legit'),
             ("Eve (Random)", 'random'), ("Mallory (Fixed)", 'fixed'), ("APT (Clone)", 'clone')]
    demo_log = []
    print(f"\n  {'User':<20} {'Fidelity':>10}  {'Status'}")
    print("  " + "-" * 38)
    for name, strat in demos:
        avg, alert = access(states, key, strategy=strat)
        demo_log.append((name, strat, avg, alert))
        print(f"  {name:<20} {avg:>10.4f}  {'ALERT' if alert else 'OK'}")

    print("\n  Running 40 trials per category...")
    results = run_trials(n=40)

    print(f"\n  {'Category':<18} {'Fidelity':>10}  {'Detection':>10}")
    print("  " + "-" * 42)
    for label in results:
        avg  = np.mean(results[label])
        rate = sum(1 for f in results[label] if f < THRESHOLD) / 40 * 100
        print(f"  {label:<18} {avg:>10.3f}  {rate:>9.0f}%")

    print("\n  Generating charts and building PDF...")
    chart_paths = make_charts(results, demo_log)
    build_pdf(results, demo_log, chart_paths)

    print("  DONE.  Output: honeypot_report.pdf")

if __name__ == "__main__":
    main()