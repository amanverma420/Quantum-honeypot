# QuantumGuard Enterprise Architecture Specification

## 1. System Components & Flow

```mermaid
graph TD
    subgraph Attacker Facing Traps
        T1[Decoy HTTP Gateway :8080]
        T2[Decoy SSH Bastion :2222]
        T3[Canary Filesystem Watcher]
    end

    subgraph Central Event Pipeline
        P1[Schema Validation & Normalization]
        P2[Credential & Secret Redaction]
        P3[Deduplication & Rate Limiting]
        P4[Detection Rule Engine]
    end

    subgraph Storage & Correlation
        DB[(PostgreSQL / SQLite)]
        I1[Incident Auto-Correlation]
        AL[Audit Logging & SIEM File]
    end

    subgraph Enterprise Management & SOC
        API[FastAPI Hardened Management API :8000]
        SSE[Server-Sent Events Stream /api/v1/soc/stream]
        UI[Glassmorphism Web Dashboard]
    end

    subgraph Quantum Laboratory
        QC1[Single-Qubit Bloch Engine]
        QC2[Arbitrary Circuit Simulator]
        QC3[Bell CHSH Inequality Tester]
        QC4[BB84 QKD Protocol Simulator]
        QC5[Grover Search Demonstration]
    end

    T1 -->|Raw Access| P1
    T2 -->|Credentials| P1
    T3 -->|File Touch| P1
    P1 --> P2 --> P3 --> P4
    P4 -->|Persist Event & Alert| DB
    P4 -->|Link Incident| I1
    P4 -->|Write JSONL| AL
    P4 -->|Broadcast| SSE
    SSE -->|Live Updates| UI
    UI -->|REST Operations| API
    API -->|Query / Update| DB
    UI -->|Simulate & Research| QC1
    UI -->|Circuits| QC2
    UI -->|Entanglement| QC3
    UI -->|QKD Protocol| QC4
    UI -->|Search| QC5
```

---

## 2. Trust Boundaries & Separation of Concerns

1. **Management Interface vs Attacker Honeypot Separation**:
   - Management API and Dashboard run on Port `8000`, protected by PBKDF2 password hashing, JWT bearer tokens, and server-side RBAC.
   - Attacker-facing HTTP decoy runs on Port `8080` and SSH decoy on Port `2222`.
   - Attacker traps have zero read access to management APIs, users, or active incidents.
2. **Deterministic Credential Redaction**:
   - Passwords and auth cookies received by decoy traps are automatically sanitized via recursive pattern matching prior to being persisted or broadcast to the SSE stream.
3. **Scientific Realism Separation**:
   - Deception events represent real-world observed accesses to decoy files or honeypot ports.
   - The Quantum Laboratory is a modular research and simulation engine running density-matrix and statevector mathematics. Quantum simulation does not physically protect classical data.
