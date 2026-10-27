"""Decoy HTTP REST Gateway & Canary Web Trap."""

import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Any

from .base import BaseTrapDaemon
from ..tokens.registry import REGISTRY
from ..tokens.verifier import verify_token_access
from ..detection.alerts import DISPATCHER
from ..detection.siem_logger import SIEM_LOG_FILE

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class DecoyHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "QuantumGuard-Gateway/2.4"
    sys_version = ""

    def _send_json(self, status: int, data: Dict[str, Any]):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: int, text: str, content_type: str = "text/plain"):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        client_ip = self.client_address[0]
        user_agent = self.headers.get("User-Agent", "Unknown")

        # 1. Decoy Root
        if path in ("/", "/index.html"):
            html = """<!DOCTYPE html>
<html>
<head><title>Internal Cloud Enterprise Portal - QuantumGuard</title>
<style>body{font-family:sans-serif;background:#0d1117;color:#c9d1d9;padding:40px;text-align:center;}
.box{max-width:500px;margin:auto;background:#161b22;padding:30px;border-radius:8px;border:1px solid #30363d;}
input{width:90%;padding:10px;margin:8px 0;background:#0d1117;border:1px solid #30363d;color:#fff;}
button{padding:10px 20px;background:#238636;color:#fff;border:none;border-radius:4px;cursor:pointer;}
</style></head>
<body><div class="box"><h2>QuantumGuard Core Node</h2><p>Restricted Corporate Access</p>
<form method="POST" action="/login"><input type="text" placeholder="Username" /><br>
<input type="password" placeholder="Password" /><br><button type="submit">Sign In</button></form>
</div></body></html>"""
            self._send_text(200, html, "text/html")
            return

        # 2. Decoy Environment / Config Leak Traps (.env, /admin/config.env, etc.)
        if path in ("/.env", "/admin/config.env", "/config.env", "/.git/config"):
            tokens = REGISTRY.list_tokens()
            db_tok = REGISTRY.find_matching_token("postgresql")
            stripe_tok = REGISTRY.find_matching_token("qg_live")
            aws_tok = REGISTRY.find_matching_token("AKIA")

            env_content = f"""# PRODUCTION ENVIRONMENT CONFIG (CONFIDENTIAL)
APP_ENV=production
DEBUG=false
APP_SECRET=sec_quantum_enc_74920491823

# Database Cluster
DATABASE_URL={db_tok.decoy_secret if db_tok else 'postgresql://db_admin:qg_sec_pass@prod-db.internal:5432/core'}

# Stripe Live Gateway
STRIPE_SECRET_KEY={stripe_tok.decoy_secret if stripe_tok else 'qg_live_demo_key_9934'}

# AWS IAM Backup Bucket
AWS_ACCESS_KEY_ID={aws_tok.decoy_secret.split(':')[0] if aws_tok else 'AKIAIOSFODNN7EXAMPLE'}
AWS_SECRET_ACCESS_KEY={aws_tok.decoy_secret.split(':')[1] if aws_tok and ':' in aws_tok.decoy_secret else 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'}
"""
            # Fire alert for unauthorized config probe
            DISPATCHER.dispatch(
                event_type="api_key",
                token_id="ENV_LEAK_HONEYTOKEN",
                target_service="Decoy .env Configuration File",
                source_ip=client_ip,
                fidelity=0.62,
                threshold=0.85,
                is_attack=True,
                extra={"requested_path": path, "user_agent": user_agent}
            )
            self._send_text(200, env_content)
            return

        # 3. Decoy AWS metadata probe
        if "metadata" in path or "security-credentials" in path:
            aws_tok = REGISTRY.find_matching_token("AKIA")
            cred_json = {
                "Code": "Success",
                "LastUpdated": "2026-10-27T12:00:00Z",
                "Type": "AWS-HMAC",
                "AccessKeyId": aws_tok.decoy_secret.split(':')[0] if aws_tok else "AKIA_CANARY_PROD",
                "SecretAccessKey": aws_tok.decoy_secret.split(':')[1] if aws_tok and ':' in aws_tok.decoy_secret else "CANARY_SECRET",
                "Token": "CANARY_SECURITY_TOKEN",
                "Expiration": "2026-10-28T00:00:00Z"
            }
            DISPATCHER.dispatch(
                event_type="aws_iam",
                token_id=aws_tok.token_id if aws_tok else "AWS_METADATA_PROBE",
                target_service="Decoy AWS IAM Metadata Instance",
                source_ip=client_ip,
                fidelity=0.55,
                threshold=0.85,
                is_attack=True,
                extra={"path": path, "user_agent": user_agent}
            )
            self._send_json(200, cred_json)
            return

        # 4. Honeytoken Status Endpoint
        if path == "/api/v1/quantum/status":
            self._send_json(200, {
                "status": "ONLINE",
                "system": "Quantum Honeypot Intrusion Detection System",
                "engine_version": "2.0.0",
                "active_honeytokens": len(REGISTRY._tokens_by_id),
                "tokens": REGISTRY.list_tokens()
            })
            return

        # 5. Fallback 404
        self._send_json(404, {"error": "Not Found", "path": path})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        client_ip = self.client_address[0]
        user_agent = self.headers.get("User-Agent", "Unknown")

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""

        # 1. Quantum Token Verification Endpoint
        if path == "/api/v1/quantum/verify":
            try:
                payload = json.loads(body) if body else {}
                token_id = payload.get("token_id")
                token_secret = payload.get("secret")
                strategy = payload.get("strategy", "random")

                token = None
                if token_id:
                    token = REGISTRY.get_by_id(token_id)
                elif token_secret:
                    token = REGISTRY.get_by_secret(token_secret) or REGISTRY.find_matching_token(token_secret)

                if not token:
                    self._send_json(404, {"error": "Token not found in registry"})
                    return

                res = verify_token_access(
                    token=token,
                    strategy=strategy,
                    source_ip=client_ip,
                    user_agent=user_agent
                )

                DISPATCHER.dispatch(
                    event_type=token.token_type,
                    token_id=token.token_id,
                    target_service=token.target_service,
                    source_ip=client_ip,
                    fidelity=res.mean_fidelity,
                    threshold=res.threshold,
                    is_attack=res.is_intrusion,
                    extra={"strategy": strategy, "user_agent": user_agent}
                )

                self._send_json(200, res.to_dict())
                return
            except Exception as e:
                self._send_json(500, {"error": str(e)})
                return

        # 2. Fake login endpoint (capture brute force credentials)
        if path == "/login":
            DISPATCHER.dispatch(
                event_type="bruteforce",
                token_id="PORTAL_AUTH",
                target_service="Web Portal Auth Form",
                source_ip=client_ip,
                fidelity=0.48,
                threshold=0.85,
                is_attack=True,
                extra={"payload_preview": body[:100]}
            )
            self._send_json(401, {"error": "Invalid enterprise credentials"})
            return

        self._send_json(404, {"error": "Endpoint not found"})

    def log_message(self, format, *args):
        # Suppress default stdout spew
        return

class DecoyHTTPTrap(BaseTrapDaemon):
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        super().__init__(name="Decoy HTTP Gateway Trap", host=host, port=port)
        self.server: ThreadedHTTPServer = None

    def _run(self):
        REGISTRY.bootstrap_default_decoys()
        try:
            self.server = ThreadedHTTPServer((self.host, self.port), DecoyHTTPRequestHandler)
            self.server.serve_forever()
        except Exception as e:
            print(f"[!] HTTP Trap Error on {self.host}:{self.port}: {e}")

    def stop(self):
        if self.server:
            self.server.shutdown()
        super().stop()
