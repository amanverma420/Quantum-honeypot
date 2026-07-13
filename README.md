# ⚛️ QuantumGuard — Quantum Honeypot System

[![Vercel Deployment](https://img.shields.io/badge/deploy-vercel-black?logo=vercel)](https://vercel.com/)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Qiskit Simulation](https://img.shields.io/badge/physics-Qiskit-purple)](https://qiskit.org/)

An intrusion detection system leveraging the principles of **quantum mechanics** (such as superposition, the observer effect, state fidelity, and the no-cloning theorem) to protect critical system assets. By embedding quantum state tripwires within credential honeytokens, silent reading or cloning of secrets becomes physically impossible.

### 🌐 Live Dashboard Demo
**Access the live web-based control center here:**  
👉 **[https://quantum-honeypot.vercel.app](https://quantum-honeypot.vercel.app)** (Or your customized Vercel URL)

---

## 📌 Project Overview

QuantumGuard simulates a **quantum-enhanced honeypot** network.

Unlike classical honeytokens (decoy database passwords, API keys, or cloud credentials) which can be copied, cloned, or silently read without immediate detection, QuantumGuard embeds **quantum tripwire qubits** inside decoy assets.
* **Observer Effect**: An attacker attempting to observe or read the protected token is forced to measure the qubits. Because the secret basis is server-side only, they guess bases, collapsing the superposition states and introducing a measurable fidelity drop.
* **No-Cloning Theorem**: It is physically impossible for an attacker to copy the state of the qubits to analyze them later. Duplication attempts introduce noise, dragging the fidelity down to ~38% and triggering instant alerts.

---

## 🚀 Key Features

* **Quantum Sandbox & Cryptography Lab**: A visual playground to build qubit circuits, apply Hadamard (H) and Pauli-X (X) gates, adjust depolarizing channel noise, simulate fiber alignment polarization angles, and measure outcomes in real-time.
* **BB84 QKD Visualizer**: A step-by-step interactive walk-through showing Alice preparing qubits, Eve eavesdropping, Bob measuring, and how sifting/reconciling reveals Eve's footprint (25% error rate).
* **SOC Network Threat Map**: A live canvas visualization mapping client-to-host tracer lines and showing packet traffic routes with interactive visual indicators during credential accesses.
* **ROC & Confusion Matrix Analytics**: Dynamic charts representing True Positives, False Positives, False Negatives, and True Negatives, alongside a Receiver Operating Characteristic (ROC) curve that recalculates in real-time as the alert threshold slider is modified.
* **Statistical Simulation Lab**: Batch runs (40-160 trials) analyzing mean fidelity, standard deviation, and alarm rates across Legitimate, Random Guessing, Fixed Basis, and Clone attempts.
* **Technical Report Generator**: Generate and print comprehensive PDF scientific reports compiling active session telemetry.

---

## 🏗 Directory Structure

```bash
Quantum-honeypot/
├── .github/
│   └── workflows/
│       └── static.yml           # GitHub Actions static deploy workflow
├── charts/
│   ├── chart_boxplot.png       # Boxplot fidelity distribution
│   ├── chart_detection.png     # Detection bar chart
│   ├── chart_fidelity.png      # Average fidelity bar chart
│   └── chart_trials.png        # Per-trial fidelity line plot
├── js/
│   ├── app.js                  # SOC dashboard controller, sandbox & QKD logic
│   └── quantum_engine.js       # Browser-based Quantum circuit simulator
├── screenshots/
│   └── (Interface previews)
├── index.html                  # Main control center dashboard
├── styles.css                  # Custom cyberpunk glassmorphism stylesheet
├── quantum_honeypot.py         # Python simulation & ReportLab PDF generator
├── honeypot_report.pdf         # Compiled project evaluation report
└── README.md                   # Project overview & documentation
```

---

## 🖥 Dashboard Control Center

### 1. Dashboard
* **SOC Monitoring**: Live access counters, audit logs, and threat indicators (LOW to CRITICAL).
* **Honeytoken Decoys**: Panels representing Decoy DB, API, and S3 credentials wrapped with a quantum tripwire layer.
* **Trace Map**: Interactive canvas drawing trace lines and animating glowing packet pulses when accesses occur.

### 2. Simulate
* **Malicious Vectors**: Evaluate Random Basis, Fixed Basis, and Clone Attempt strategies.
* **State collapse**: View per-qubit fidelity grids showing the collapse of individual register elements.

### 3. Sandbox & QKD
* **Circuit Workspace**: Add gates and customize measurement parameters (noise/offset).
* **QKD BB84 Walkthrough**: Step through key distribution stages and calculate sifted key error rates.

### 4. Analytics
* **Statistical Telemetry**: Compute means, standard deviations, and alarm counts.
* **ROC Curve**: Real-time evaluation of True Positive vs False Positive rates under different thresholds.

---

## ⚙️ Execution & Setup

### 🌐 Web Dashboard (Browser)
The dashboard runs entirely in the client-side browser with zero configuration:
1. Open `index.html` in any modern web browser.
2. Alternatively, view the hosted page: **[https://amanverma420.github.io/Quantum-honeypot/](https://amanverma420.github.io/Quantum-honeypot/)**.

### 🐍 CLI Python Simulation (PDF Report Compilation)
To execute the backend simulation and compile a PDF technical report:
1. Install Python dependencies:
   ```bash
   pip install numpy matplotlib reportlab
   ```
2. Run the script:
   ```bash
   python quantum_honeypot.py
   ```
3. A file named `honeypot_report.pdf` and refreshed analysis charts will be generated in the root directory.

---

## 🛠 Deployment Configuration

You can host this static dashboard easily using **Vercel** or **Netlify**:

### Option A: Vercel Dashboard (Recommended)
1. Go to [Vercel](https://vercel.com) and sign in.
2. Click **Add New -> Project**.
3. Import your GitHub repository: `https://github.com/amanverma420/Quantum-honeypot`.
4. Vercel will automatically detect the static project. Leave default settings and click **Deploy**.
5. Vercel will build the files and provide a live sharing link (e.g. `https://quantum-honeypot.vercel.app`), which will auto-redeploy on every `git push`.

### Option B: Netlify Dashboard
1. Go to [Netlify](https://netlify.com) and log in.
2. Click **Add new site -> Import an existing project**.
3. Choose **GitHub** and select the `Quantum-honeypot` repository.
4. Leave the build command empty, set the publish directory to `.` (root), and click **Deploy site**.

---

## 📚 References
* W. K. Wootters and W. H. Zurek, *"A single quantum cannot be cloned,"* Nature, vol. 299, pp. 802–803, 1982.
* C. H. Bennett and G. Brassard, *"Quantum Cryptography: Public key distribution and coin tossing,"* Proc. IEEE Int. Conf. on Computers, Systems and Signal Processing, 1984.
* M. A. Nielsen and I. L. Chuang, *"Quantum Computation and Quantum Information,"* Cambridge University Press, 2010.

---
COEP Technological University, Pune  
Department of Computer Science & Engineering
