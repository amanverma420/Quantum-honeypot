# QuantumGuard Security Model & Threat Assessment

## 1. Authentication & Role-Based Access Control (RBAC)

- **Password Storage**: NIST SP 800-63B compliant `PBKDF2-HMAC-SHA256` with `600,000` iterations and a 16-byte cryptographically secure random salt generated via `secrets.token_bytes()`.
- **Session Tokens**: Tamper-proof HMAC-SHA256 signed bearer tokens with explicit `exp` expiration, `iat` timestamp, and constant-time signature verification.
- **Server-Side Enforcement**:
  - `Admin`: Full system configuration, user provisioning, audit logging, decoy management.
  - `Analyst`: Incident investigation, alert acknowledgement, manual note annotation, security drill execution.
  - `Viewer`: Read-only access to filtered events, analytics, and sanitized CSV/JSON report exports.

---

## 2. Decoy Traps & Attacker Containment

| Trap Component | Interface | Containment Model | Mitigations |
|---|---|---|---|
| **HTTP Decoy** | TCP 8080 | Emulated Web Portal / Fake Cloud Metadata | No access to local host filesystem; management APIs disabled on this port. |
| **SSH Bastion** | TCP 2222 | Emulated OpenSSH Shell Prompt | Fake restricted command interpreter (`ls`, `whoami`, `cat`). No subshell execution or shell access on host. |
| **Filesystem Canaries** | Local OS | Monitored Files (`.ini`, `.conf`, `.json`) | Synthetic credentials only. Monitored for access events without execution hooks. |

---

## 3. MITRE ATT&CK Framework Mapping

| Rule ID | MITRE Technique ID | Technique Name | Evidence Source |
|---|---|---|---|
| `RULE-HONEYTOKEN-01` | `T1552.001` | Unsecured Credentials: In Files | Access to honeytokens (`api_key`, `database`, `ssh_key`) |
| `RULE-METADATA-02` | `T1552.005` | Unsecured Credentials: Cloud Metadata | Probe to `/latest/meta-data` or `/security-credentials` |
| `RULE-AUTH-03` | `T1110` | Brute Force | Multiple failed logins against web portal or SSH decoy |
| `RULE-CORRELATION-04` | `T1046` | Network Service Discovery | Same source IP touching $\ge 2$ distinct decoys in 5 mins |
| `RULE-CANARY-05` | `T1565.001` | Data Manipulation: Stored Data | Canary file access or timestamp update |

---

## 4. Responsible Disclosure & Security Reporting

To report security vulnerabilities or misconfigurations, please contact the repository security maintainers or open a confidential security advisory on GitHub.
