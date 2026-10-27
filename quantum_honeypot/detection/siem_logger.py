"""SIEM Logging and MITRE ATT&CK Structured Event Producer."""

import os
import json
import time
from typing import Dict, Any, Optional

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
SIEM_LOG_FILE = os.path.join(LOG_DIR, "quantum_siem_events.jsonl")

MITRE_TECHNIQUES = {
    "api_key": {"id": "T1552.001", "name": "Unsecured Credentials: Credentials In Files"},
    "database": {"id": "T1078.003", "name": "Valid Accounts: Local Accounts"},
    "aws_iam": {"id": "T1552.005", "name": "Unsecured Credentials: Cloud Instance Metadata API"},
    "ssh_key": {"id": "T1552.004", "name": "Unsecured Credentials: Private Keys"},
    "clone": {"id": "T1565.002", "name": "Data Manipulation: Runtime Data Modification"},
    "scan": {"id": "T1046", "name": "Network Service Discovery"},
    "bruteforce": {"id": "T1110", "name": "Brute Force"}
}

def log_security_event(
    event_type: str,
    severity: str,
    message: str,
    source_ip: str,
    token_id: Optional[str] = None,
    fidelity: Optional[float] = None,
    chsh_s: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Emit a structured SIEM event compliant with Elastic Common Schema (ECS)."""
    technique = MITRE_TECHNIQUES.get(event_type, {"id": "T1005", "name": "Data from Local System"})
    
    event = {
        "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": {
            "kind": "alert" if severity in ("HIGH", "CRITICAL") else "event",
            "category": ["intrusion_detection", "quantum_security"],
            "type": ["access", "denied" if severity in ("HIGH", "CRITICAL") else "allowed"],
            "severity": severity,
            "action": event_type
        },
        "message": message,
        "source": {
            "ip": source_ip
        },
        "quantum_telemetry": {
            "token_id": token_id,
            "fidelity": fidelity,
            "chsh_s_value": chsh_s,
            "physics_invariant_violated": fidelity is not None and fidelity < 0.85
        },
        "threat": {
            "framework": "MITRE ATT&CK",
            "technique": technique
        },
        "labels": extra or {}
    }

    # Append to JSONL log
    try:
        with open(SIEM_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print(f"[LOG ERROR] Could not write SIEM log: {e}")

    return event
