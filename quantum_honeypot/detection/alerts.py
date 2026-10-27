"""Alert Dispatcher Bridge routing all trap and simulation detections through PIPELINE."""

from typing import Dict, Any, Optional
from ..db.database import SessionLocal
from ..schemas.models import SecurityEventCreate
from .pipeline import PIPELINE

class AlertDispatcher:
    def __init__(self):
        self.active_alarms = []

    def dispatch(
        self,
        event_type: str,
        token_id: str,
        target_service: str,
        source_ip: str,
        fidelity: float,
        threshold: float,
        is_attack: bool,
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format and dispatch security alerts through central event pipeline."""
        severity = "CRITICAL" if fidelity < 0.60 else ("HIGH" if is_attack else "INFO")
        
        if is_attack:
            status_text = "[!] HONEYTOKEN BREACH TRIPWIRE ACTIVATED"
            msg = (
                f"Intruder accessed honeytoken '{token_id}' for '{target_service}' from {source_ip}. "
                f"Synthetic credential compromised. Quantum simulation telemetry: F={fidelity:.4f} (Threshold: {threshold:.2f})."
            )
        else:
            status_text = "[+] LEGITIMATE SECRET VERIFICATION"
            msg = (
                f"Legitimate verification for {token_id} at '{target_service}' from {source_ip}. "
                f"Telemetry: F={fidelity:.4f}."
            )

        evidence = extra.copy() if extra else {}
        evidence["target_service"] = target_service
        evidence["threshold"] = threshold

        event_create = SecurityEventCreate(
            event_type=event_type,
            severity=severity,
            message=msg,
            source_ip=source_ip,
            sensor_id="gateway-default",
            token_id=token_id,
            evidence=evidence,
            quantum_telemetry={"fidelity": fidelity, "threshold": threshold, "is_attack": is_attack}
        )

        with SessionLocal() as db:
            db_event, alert = PIPELINE.ingest(event_create, db)

        # Print banner to console
        if is_attack:
            print("\n" + "=" * 70)
            print(f" {status_text} [{severity}]")
            print("=" * 70)
            print(f" Target Asset : {target_service}")
            print(f" Honeytoken   : {token_id}")
            print(f" Attacker IP  : {source_ip}")
            print(f" Qubit Sim Fid: {fidelity:.4f} (Simulated Bound < {threshold:.2f})")
            print(f" MITRE ATT&CK : {db_event.mitre_technique_id} - {db_event.mitre_technique_name}")
            print("=" * 70 + "\n")

        alarm_record = {
            "status": status_text,
            "severity": severity,
            "token_id": token_id,
            "service": target_service,
            "fidelity": fidelity,
            "source_ip": source_ip,
            "time": db_event.timestamp.isoformat()
        }
        self.active_alarms.append(alarm_record)

        return {
            "id": db_event.id,
            "timestamp": db_event.timestamp.isoformat(),
            "severity": severity,
            "message": msg,
            "source_ip": source_ip
        }

DISPATCHER = AlertDispatcher()
