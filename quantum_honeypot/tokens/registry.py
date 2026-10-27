"""Quantum Honeytoken Registry for tracking, persistence, and state management."""

import json
import time
from typing import Dict, List, Optional
from .generator import QuantumHoneytoken, generate_honeytoken

class TokenRegistry:
    def __init__(self):
        self._tokens_by_id: Dict[str, QuantumHoneytoken] = {}
        self._tokens_by_secret: Dict[str, QuantumHoneytoken] = {}

    def register(self, token: QuantumHoneytoken) -> QuantumHoneytoken:
        """Register a new active honeytoken."""
        self._tokens_by_id[token.token_id] = token
        self._tokens_by_secret[token.decoy_secret] = token
        return token

    def get_by_id(self, token_id: str) -> Optional[QuantumHoneytoken]:
        return self._tokens_by_id.get(token_id)

    def get_by_secret(self, secret: str) -> Optional[QuantumHoneytoken]:
        return self._tokens_by_secret.get(secret)

    def find_matching_token(self, text: str) -> Optional[QuantumHoneytoken]:
        """Check if any registered honeytoken secret is contained in text or input."""
        for secret, token in self._tokens_by_secret.items():
            if secret in text or token.token_id in text:
                return token
        return None

    def list_tokens(self) -> List[Dict[str, any]]:
        """Return metadata summary of all registered honeytokens."""
        return [
            {
                "token_id": t.token_id,
                "token_type": t.token_type,
                "target_service": t.target_service,
                "decoy_secret_preview": t.decoy_secret[:24] + "...",
                "n_tripwires": t.n_tripwires,
                "status": t.status,
                "access_count": len(t.access_history),
                "created_at": t.created_at
            }
            for t in self._tokens_by_id.values()
        ]

    def bootstrap_default_decoys(self):
        """Seed registry with production-grade decoy tokens."""
        if not self._tokens_by_id:
            self.register(generate_honeytoken("api_key", "Production Stripe API Gateway", n_qubits=8))
            self.register(generate_honeytoken("database", "Core Financial Postgres Cluster", n_qubits=8))
            self.register(generate_honeytoken("aws_iam", "AWS IAM S3 Backup Operator", n_qubits=8))
            self.register(generate_honeytoken("ssh_key", "Bastion Host Root SSH Key", n_qubits=8))

# Global registry singleton
REGISTRY = TokenRegistry()
