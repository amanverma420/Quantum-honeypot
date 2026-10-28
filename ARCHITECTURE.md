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
        P1[Pydantic Schema Validation]
        P2[Credential & Secret Redaction]
        P3[Event Persistence]
        P4[Detection Rule Engine]
        P5[Alert & Incident Correlation]
    end

    subgraph Storage & Correlation
        DB[(PostgreSQL / SQLite)]
        I1[Incident Auto-Correlation]
        AL[Audit Logging & SIEM File]
    end

    subgraph Enterprise Management & SOC
        API[FastAPI Hardened Management API :8000]
        SSE[Server-Sent Events Stream /api/v1/soc/stream]
        UI[Authenticated SOC Dashboard & Demo Center]
    end

    subgraph Quantum Laboratory
        QC1[Single-Qubit Bloch Engine]
        QC2[Arbitrary Circuit Simulator]
        QC3[Bell CHSH Inequality Tester]
        QC4[BB84 QKD Protocol Simulator]
        QC5[Grover Search Demonstration]
        QC6[Noise & Repetition-Code Lab]
        QC7[Bell-State & Teleportation Lab]
        QC8[Seeded Search Benchmark]
    end

    T1 -->|Raw Access| P1
    T2 -->|Credentials| P1
    T3 -->|File Touch| P1
    P1 --> P2 --> P3 --> P4 --> P5
    P3 --> DB
    P5 -->|Persist Alert & Incident| DB
    P5 --> I1
    P5 -->|Write JSONL & Audit| AL
    P5 -->|Broadcast| SSE
    SSE -->|Live Updates| UI
    UI -->|REST Operations| API
    API -->|Query / Update| DB
    UI -->|Simulate & Research| QC1
    UI -->|Circuits| QC2
    UI -->|Entanglement| QC3
    UI -->|QKD Protocol| QC4
    UI -->|Search| QC5
    UI --> QC6
    UI --> QC7
    UI --> QC8
    UI -->|Synthetic scenarios through pipeline| P1
```

---

## 2. Trust Boundaries & Separation of Concerns

1. **Management Interface vs Attacker Honeypot Separation**:
   - Management API and Dashboard run on Port `8000`; SOC telemetry requires authenticated viewer access, while writes require analyst/admin roles. New administrator bootstrap credentials are configured by environment.
   - Attacker-facing HTTP decoy runs on Port `8080` and SSH decoy on Port `2222`.
   - Attacker traps have zero read access to management APIs, users, or active incidents.
2. **Deterministic Credential Redaction**:
   - Passwords and auth cookies received by decoy traps are automatically sanitized via recursive pattern matching prior to being persisted or broadcast to the SSE stream.
3. **Scientific Realism Separation**:
   - Deception events may be genuine trap telemetry or explicitly labeled synthetic demo data. Synthetic demos use the same event pipeline and have per-run cleanup.
   - The Quantum Laboratory is a modular research simulator running density-matrix and statevector mathematics. Quantum simulation does not physically protect classical data or generate SOC detections.
