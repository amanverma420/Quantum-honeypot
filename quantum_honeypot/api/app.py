"""FastAPI Enterprise Application for QuantumGuard Deception & SOC Platform."""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..db.database import get_db, init_db
from ..db.models import User
from ..security.auth import validate_security_configuration
from .auth_router import router as auth_router
from .soc_router import router as soc_router
from .quantum_router import router as quantum_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_security_configuration()
    init_db()
    yield


_logger = logging.getLogger(__name__)

app = FastAPI(
    title="QuantumGuard Enterprise Platform API",
    description="Deception Technology, Honeypot Intrusion Detection, and Quantum Computing Research Laboratory",
    version="3.0.0",
    lifespan=lifespan
)

# CORS configuration
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router)
app.include_router(soc_router)
app.include_router(quantum_router)

@app.get("/healthz", tags=["System Health"])
def health_check():
    """Liveness check endpoint."""
    return {"status": "HEALTHY", "service": "quantumguard-api", "version": "3.0.0"}

@app.get("/readyz", tags=["System Health"])
def readiness_check(db: Session = Depends(get_db)):
    """Readiness check validating database and core service availability."""
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            return JSONResponse(status_code=503, content={"status": "NOT_READY", "reason": "Admin user missing"})
        return {"status": "READY", "database": "CONNECTED"}
    except SQLAlchemyError:
        _logger.exception("Database readiness probe failed.")
        return JSONResponse(status_code=503, content={"status": "NOT_READY", "reason": "Database unavailable"})

# Mount static frontend directory for unified deployment
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JS_DIR = os.path.join(ROOT_DIR, "js")
CHARTS_DIR = os.path.join(ROOT_DIR, "charts")

if os.path.exists(JS_DIR):
    app.mount("/js", StaticFiles(directory=JS_DIR), name="js")
if os.path.exists(CHARTS_DIR):
    app.mount("/charts", StaticFiles(directory=CHARTS_DIR), name="charts")

@app.get("/", include_in_schema=False)
def serve_dashboard():
    index_path = os.path.join(ROOT_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "QuantumGuard Enterprise API is operational. Visit /docs for OpenAPI documentation."}

@app.get("/styles.css", include_in_schema=False)
def serve_styles():
    css_path = os.path.join(ROOT_DIR, "styles.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    return JSONResponse(status_code=404, content={"error": "styles.css not found"})

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)
