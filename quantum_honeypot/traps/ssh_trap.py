"""Decoy SSH & Interactive Terminal Honeypot Trap."""

import socket
import threading
from typing import Optional

from .base import BaseTrapDaemon
from ..tokens.registry import REGISTRY
from ..detection.alerts import DISPATCHER

class DecoySSHTrap(BaseTrapDaemon):
    def __init__(self, host: str = "127.0.0.1", port: int = 2222):
        super().__init__(name="Decoy SSH Honeypot", host=host, port=port)
        self._sock: Optional[socket.socket] = None

    def _run(self):
        REGISTRY.bootstrap_default_decoys()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._sock.bind((self.host, self.port))
            self._sock.listen(10)
        except Exception as e:
            print(f"[!] Could not bind SSH trap to {self.host}:{self.port} (Port may be in use): {e}")
            self.is_running = False
            return

        while self.is_running:
            try:
                conn, addr = self._sock.accept()
                client_thread = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                client_thread.start()
            except Exception:
                break

    def _handle_client(self, conn: socket.socket, addr: tuple):
        client_ip = addr[0]
        try:
            conn.settimeout(15)
            # Send OpenSSH banner
            conn.sendall(b"SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6\r\n")
            
            client_banner = conn.recv(1024).decode("utf-8", errors="ignore").strip()
            
            # Simple interactive fake shell emulation
            conn.sendall(b"\r\n=== RESTRICTED ENTERPRISE BASTION SHELL ===\r\n")
            conn.sendall(b"login as: ")
            username = conn.recv(1024).decode("utf-8", errors="ignore").strip()
            conn.sendall(f"{username}@bastion's password: ".encode("utf-8"))
            password = conn.recv(1024).decode("utf-8", errors="ignore").strip()

            # Dispatch brute force event
            DISPATCHER.dispatch(
                event_type="bruteforce",
                token_id="SSH_LOGIN_CANARY",
                target_service="Bastion SSH Gateway",
                source_ip=client_ip,
                fidelity=0.50,
                threshold=0.85,
                is_attack=True,
                extra={"user": username, "password_attempt": "[REDACTED_PASSWORD]", "client_banner": client_banner}
            )

            # Let attacker into a fake restricted shell
            conn.sendall(b"\r\nLast login: Mon Oct 27 18:22:10 2026 from 10.0.4.12\r\n")
            conn.sendall(b"bastion:~$ ")

            while self.is_running:
                cmd = conn.recv(1024).decode("utf-8", errors="ignore").strip()
                if not cmd or cmd in ("exit", "quit"):
                    break

                if cmd == "ls":
                    conn.sendall(b"aws_keys.env  database_prod.conf  id_rsa_quantum\r\nbastion:~$ ")
                elif cmd == "pwd":
                    conn.sendall(b"/home/admin\r\nbastion:~$ ")
                elif cmd == "whoami":
                    conn.sendall(b"admin\r\nbastion:~$ ")
                elif "cat" in cmd:
                    # Attacker accessing bait file
                    ssh_tok = REGISTRY.find_matching_token("OPENSSH") or REGISTRY.find_matching_token("qtok")
                    tok_id = ssh_tok.token_id if ssh_tok else "SSH_KEY_TRIPWIRE"
                    
                    DISPATCHER.dispatch(
                        event_type="ssh_key",
                        token_id=tok_id,
                        target_service="Decoy Bastion Key Vault",
                        source_ip=client_ip,
                        fidelity=0.38,
                        threshold=0.85,
                        is_attack=True,
                        extra={"command": cmd}
                    )
                    conn.sendall(f"{ssh_tok.decoy_secret if ssh_tok else 'FAKE_KEY'}\r\nbastion:~$ ".encode("utf-8"))
                else:
                    conn.sendall(f"bash: {cmd}: command restricted by security policy\r\nbastion:~$ ".encode("utf-8"))

        except Exception:
            pass
        finally:
            conn.close()

    def stop(self):
        super().stop()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
