# QuantumGuard Enterprise — Production Deployment Guide

This guide covers deploying the **QuantumGuard Enterprise Deception and SOC Platform** for production pilots, cloud environments, and containerized Docker setups.

---

## 1. Architecture Overview

QuantumGuard is architected as a hardened modular platform:
- **Backend & API**: Python 3.11 / FastAPI running asynchronous endpoints, detection rules, and Server-Sent Events (SSE).
- **Database Layer**: SQLAlchemy ORM with SQLite for zero-config local development, and PostgreSQL 16+ for enterprise production.
- **Frontend SOC Dashboard**: Single-Page Web Dashboard communicating via REST API and live SSE stream (`/api/v1/soc/stream`).
- **Access Control**: Operational SOC data requires a bearer token; analyst/admin roles are required for changes and demo triggers.
- **Research**: Public, input-bounded quantum simulations include Kraus noise channels, repetition codes, Bell-state entanglement, teleportation, seeded BB84, and Grover benchmarks.
- **Demo Center**: Synthetic events are tagged by run ID and ingested through the same pipeline as sensor events. Quantum experiments run separately and do not produce alerts.
- **Decoy Services**: Attacker-facing isolated trap daemons (HTTP on 8080, SSH on 2222, Filesystem Canaries) reporting to the central ingestion pipeline.

---

## 2. Environment Variables

Create a production `.env` file based on `.env.example`:

| Variable | Description | Default / Example |
|---|---|---|
| `ENVIRONMENT` | Runtime environment mode | `production` |
| `PORT` | API server listen port | `8000` |
| `HOST` | API server listen host | `0.0.0.0` |
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql://user:pass@host:5432/db` |
| `JWT_SECRET_KEY` | 32+ character signing key | Generated cryptographically |
| `TOKEN_EXPIRY_SECONDS`| Bearer token validity period | `86400` (24 hours) |
| `INITIAL_ADMIN_PASSWORD` | First-run administrator password | Set via environment |
| `INITIAL_ANALYST_PASSWORD` | Optional first-run analyst password | Set via environment if needed |
| `POSTGRES_PASSWORD` | PostgreSQL password used by Compose | Unique URL-safe random string |
| `ALLOWED_ORIGINS` | Permitted frontend CORS origins | `https://your-soc-domain.com` |
| `DECOY_BIND_HOST` | Decoy trap interface binding | `127.0.0.1` (loopback by default) |

---

## 3. Docker Compose Deployment (Recommended)

The included `docker-compose.yml` provides a production-grade stack including an isolated PostgreSQL database, persistent volumes, and non-root container privileges:

```bash
# 1. Clone repository
git clone https://github.com/your-org/Quantum-honeypot.git
cd Quantum-honeypot

# 2. Configure environment
cp .env.example .env
# Set POSTGRES_PASSWORD, JWT_SECRET_KEY (32+ random bytes), and INITIAL_ADMIN_PASSWORD.
# Do not commit .env. Existing database accounts are not automatically rotated.

# 3. Launch stack
docker-compose up -d --build

# 4. Check status and health
docker-compose ps
docker-compose logs -f app
```

Once running:
- Web SOC Dashboard: `http://localhost:8000/`
- API Health Check: `http://localhost:8000/healthz`
- OpenAPI Documentation: `http://localhost:8000/docs`

---

## 4. Bare-Metal & Linux VM Deployment

### Step 1: Install Dependencies
```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv postgresql
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Configure Systemd Service
Create `/etc/systemd/system/quantumguard.service`:
```ini
[Unit]
Description=QuantumGuard Enterprise SOC & Deception Platform
After=network.target postgresql.service

[Service]
User=quantumguard
WorkingDirectory=/opt/quantumguard
EnvironmentFile=/opt/quantumguard/.env
ExecStart=/opt/quantumguard/venv/bin/uvicorn quantum_honeypot.api.app:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable quantumguard
sudo systemctl start quantumguard
```

---

## 5. Reverse Proxy Configuration (Nginx / Cloudflare)

Configure Nginx to terminate SSL/TLS and proxy API and SSE streams:

```nginx
server {
    listen 443 ssl http2;
    server_name soc.yourcompany.com;

    ssl_certificate /etc/letsencrypt/live/soc.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/soc.yourcompany.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Server-Sent Events (SSE) streaming requirements
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

---

## 6. Trap Containment and Network Isolation Rules

> [!CAUTION]
> **Strict Honeypot Containment Rules**:
> 1. Decoy traps (`http_trap`, `ssh_trap`, `canary_trap`) must **NEVER** run with root or administrative privileges.
> 2. Decoy traps must be bound to an isolated network segment (DMZ / VLAN) or loopback interface (`127.0.0.1`).
> 3. The SSH honeypot emulates a restricted shell and does **not** execute arbitrary host shell commands.
> 4. Internal management ports (8000) must **NEVER** be mixed with attacker-facing honeypot ports (8080, 2222).
