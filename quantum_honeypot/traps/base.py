"""Base class for Quantum Honeypot Decoy Trap Daemons."""

import threading
from typing import Optional

class BaseTrapDaemon:
    def __init__(self, name: str, host: str, port: int):
        self.name = name
        self.host = host
        self.port = port
        self.is_running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start daemon in background thread."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[*] Started {self.name} listening on {self.host}:{self.port}")

    def stop(self):
        """Stop running daemon."""
        self.is_running = False
        print(f"[*] Stopped {self.name}")

    def _run(self):
        raise NotImplementedError
