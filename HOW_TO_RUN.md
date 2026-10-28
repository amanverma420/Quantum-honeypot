# QuantumGuard — How to Run & What Everything Does

## ⚡ Quick Start (3 Steps)

```powershell
# 1. Install all dependencies
pip install -r requirements.txt

# 2. Start the full web platform (SOC dashboard + API)
uvicorn quantum_honeypot.api.app:app --host 127.0.0.1 --port 8000 --reload

# 3. Open browser → http://127.0.0.1:8000
```

---

## 🗂️ What Every File & Folder Does

### Root Files

| File | What It Does |
|------|-------------|
| `main.py` | Entry point — runs CLI commands like `simulate`, `status`, `run-traps` |
| `index.html` | The SOC (Security Operations Center) web dashboard — served at `http://127.0.0.1:8000/` |
| `styles.css` | Cyberpunk glassmorphism CSS for the dashboard |
| `quantum_honeypot.py` | Legacy standalone script (original prototype) |
| `check_assets.py` | Tests that all frontend assets (JS, CSS, charts) load correctly from the running server |
| `requirements.txt` | All Python dependencies |

---

### `quantum_honeypot/` — The Core Python Engine

```
quantum_honeypot/
├── core/           ← Quantum physics simulation engine
├── api/            ← FastAPI web server & REST endpoints
├── traps/          ← Deception trap daemons (HTTP, SSH, Canary)
├── detection/      ← Event pipeline & MITRE ATT&CK mapping
├── tokens/         ← Quantum honeytoken generator & verifier
├── reporting/      ← PDF analytics & chart generation
├── security/       ← JWT auth & password hashing
├── db/             ← SQLite database models (incidents, users)
├── schemas/        ← Pydantic request/response models
└── tests/          ← Full automated test suite (5 test files)
```

#### `core/` — Quantum Physics Modules

| File | What It Simulates |
|------|------------------|
| `quantum_lab.py` | Main simulation runner — orchestrates all 4 quantum experiments |
| `bell_chsh.py` | **Bell-CHSH inequality** — detects eavesdroppers by checking if S > 2.0 |
| `channels.py` | **Kraus noise channels** — bit-flip, phase-flip, depolarizing, amplitude damping |
| `cloning.py` | **UQCM cloning bound** — proves F ≤ 5/6 ≈ 83.33% for any copy attempt |
| `fidelity.py` | **Uhlmann fidelity** — measures how much noise degrades the quantum state |
| `gates.py` | Quantum gates — Hadamard, CNOT, Pauli X/Y/Z, Phase gates |
| `states.py` | Qubit state utilities — Bloch sphere coordinates, Bell states |
| `advanced_lab.py` | Extended experiments — BB84 decoy QKD with Wilson score confidence intervals |

#### `traps/` — Active Honeypot Daemons

| File | What It Traps |
|------|--------------|
| `http_trap.py` | Fake web server on **port 8080** — catches SQL injection, path traversal, credential harvest |
| `ssh_trap.py` | Fake SSH server on **port 2222** — catches brute-force logins, command execution |
| `canary_trap.py` | Filesystem watcher — drops fake AWS keys & DB passwords; alarms on any file read |

#### `api/` — REST API Endpoints

| File | Endpoints |
|------|----------|
| `app.py` | Main FastAPI app — serves dashboard at `/`, API docs at `/docs` |
| `quantum_router.py` | `/api/v1/quantum/*` — run CHSH, BB84, Kraus, UQCM experiments via API |
| `soc_router.py` | `/api/v1/soc/*` — real-time incident feed, SSE stream, MITRE ATT&CK mapping |
| `auth_router.py` | `/api/v1/auth/*` — JWT login, token refresh, admin management |

---

### `js/` — Dashboard Frontend

| File | What It Does |
|------|-------------|
| `app.js` | Main frontend controller — initializes dashboard, manages UI state |
| `api.js` | API client — calls the FastAPI backend endpoints |
| `dashboard.js` | Renders SOC charts, incident tables, quantum metric panels |
| `quantum_engine.js` | Runs quantum simulations visually in the browser (Bloch sphere, CHSH live plot) |
| `state.js` | Global app state management |

---

### Research Deliverables

| File/Folder | What It Is |
|-------------|-----------|
| `paper/sn-article.tex` | Full **LaTeX research paper** (Springer Nature format, 338 lines) |
| `paper/sn-bibliography.bib` | 16 academic references (strictly up to 2024) |
| `paper/fig_*.png` | 6 publication-quality figures embedded in the paper |
| `notebooks/Quantum_Honeypot_Main.ipynb` | **Jupyter notebook** — runs all 4 quantum experiments step-by-step |
| `results/quantum_honeypot_results.json` | Benchmark results (CHSH S=2.82, QBER=25.2%, MTTD=11.6ms) |
| `Quantum-Honeypot-Project-Report.pdf` | 6-chapter **project report PDF** |
| `Quantum-Honeypot-Presentation.pptx/.pdf` | 9-slide **presentation deck** |

---

## 🚀 All Ways to Run the Project

### 1. Full Web Platform (SOC Dashboard + API)
```powershell
uvicorn quantum_honeypot.api.app:app --host 127.0.0.1 --port 8000 --reload
```
- Dashboard → **http://127.0.0.1:8000/**
- API docs → **http://127.0.0.1:8000/docs**
- Health check → **http://127.0.0.1:8000/healthz**

---

### 2. CLI Commands via `python main.py`

```powershell
# Run quantum benchmark (CHSH, BB84, Kraus, UQCM) + generate charts
python main.py simulate

# Show all registered honeytokens and system status
python main.py status

# Start decoy trap daemons (HTTP :8080, SSH :2222, canary files)
python main.py run-traps

# Generate PDF report
python main.py report

# Deploy filesystem canary bait files
python main.py deploy
```

---

### 3. Research Scripts

```powershell
# Regenerate all 6 paper figures (saves to paper/ and results/figs/)
python scripts/generate_figures.py

# Rebuild the Jupyter notebook from source
python notebooks/_build_notebook.py

# Regenerate the PDF project report
python scripts/generate_report.py

# Regenerate the PPTX + PDF presentation
python scripts/generate_presentation.py
```

---

### 4. Run Tests

```powershell
pytest quantum_honeypot/tests/ -v
```

---

### 5. Check All Assets Are Loading (needs server running first)
```powershell
# Start server first, then in another terminal:
python check_assets.py
```

---

## 🔗 Key URLs When Running

| URL | What You See |
|-----|-------------|
| `http://127.0.0.1:8000/` | SOC live dashboard with quantum metrics |
| `http://127.0.0.1:8000/docs` | Interactive API documentation (Swagger UI) |
| `http://127.0.0.1:8000/redoc` | ReDoc API documentation |
| `http://127.0.0.1:8000/healthz` | System health: `{"status": "HEALTHY"}` |
| `http://127.0.0.1:8000/api/v1/quantum/status` | Quantum lab verification state |
| `http://127.0.0.1:8000/api/v1/soc/stream` | Real-time incident event stream (SSE) |

> [!TIP]
> If you want the Jupyter notebook to run interactively: `pip install jupyter` then `jupyter notebook notebooks/Quantum_Honeypot_Main.ipynb`

> [!NOTE]
> The `decoy_assets/` folder contains **fake credentials** (mock AWS keys, DB passwords) intentionally left as bait for the canary trap system — they are not real secrets.
