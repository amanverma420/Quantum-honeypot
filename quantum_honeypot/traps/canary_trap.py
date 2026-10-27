"""Filesystem Canary Files Trap & Decoy Secrets Deployer."""

import os
import json
from typing import Dict, Any, List
from .base import BaseTrapDaemon
from ..tokens.registry import REGISTRY
from ..detection.alerts import DISPATCHER

DEFAULT_CANARY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "decoy_assets")

class CanaryFilesystemTrap(BaseTrapDaemon):
    def __init__(self, target_dir: str = DEFAULT_CANARY_DIR):
        super().__init__(name="Filesystem Canary Trap", host="localhost", port=0)
        self.target_dir = target_dir
        self.tracked_files: Dict[str, float] = {}

    def deploy_canaries(self) -> List[str]:
        """Deploy honeytoken credential files into the target directory."""
        os.makedirs(self.target_dir, exist_ok=True)
        REGISTRY.bootstrap_default_decoys()
        
        deployed = []
        tokens = REGISTRY.list_tokens()
        
        # 1. AWS Credentials file
        aws_tok = REGISTRY.find_matching_token("AKIA")
        aws_path = os.path.join(self.target_dir, "aws_credentials.ini")
        with open(aws_path, "w", encoding="utf-8") as f:
            f.write(f"[default]\naws_access_key_id = {aws_tok.decoy_secret.split(':')[0] if aws_tok else 'AKIAIOSFODNN7'}\n")
            f.write(f"aws_secret_access_key = {aws_tok.decoy_secret.split(':')[1] if aws_tok and ':' in aws_tok.decoy_secret else 'sec_sample'}\n")
        deployed.append(aws_path)

        # 2. Database Connection string
        db_tok = REGISTRY.find_matching_token("postgresql")
        db_path = os.path.join(self.target_dir, "db_cluster.conf")
        with open(db_path, "w", encoding="utf-8") as f:
            f.write(f"DATABASE_URI={db_tok.decoy_secret if db_tok else 'postgresql://admin:sec@db:5432'}\n")
        deployed.append(db_path)

        # 3. API Keys JSON
        stripe_tok = REGISTRY.find_matching_token("qg_live")
        api_path = os.path.join(self.target_dir, "api_tokens.json")
        with open(api_path, "w", encoding="utf-8") as f:
            json.dump({
                "service": "payment_gateway",
                "environment": "production",
                "stripe_secret": stripe_tok.decoy_secret if stripe_tok else "qg_live_demo"
            }, f, indent=2)
        deployed.append(api_path)

        for p in deployed:
            try:
                self.tracked_files[p] = os.path.getatime(p)
            except Exception:
                pass

        print(f"[*] Deployed {len(deployed)} quantum canary files to: {self.target_dir}")
        return deployed

    def check_canaries(self) -> List[Dict[str, Any]]:
        """Check if any canary file was read or accessed."""
        alerts = []
        for file_path, orig_atime in self.tracked_files.items():
            if not os.path.exists(file_path):
                continue
            curr_atime = os.path.getatime(file_path)
            if curr_atime > orig_atime:
                basename = os.path.basename(file_path)
                alerts.append({
                    "file": basename,
                    "path": file_path,
                    "accessed_at": curr_atime
                })
                DISPATCHER.dispatch(
                    event_type="api_key",
                    token_id=f"CANARY_FILE_{basename}",
                    target_service=f"Canary File {basename}",
                    source_ip="127.0.0.1 (Local Process)",
                    fidelity=0.42,
                    threshold=0.85,
                    is_attack=True,
                    extra={"file": file_path}
                )
                self.tracked_files[file_path] = curr_atime
        return alerts
