"""Database connection and initialization module."""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, User, Sensor, Decoy

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./quantumguard.db")

# SQLite connection args for multi-threading support
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables and seed essential records if database is empty."""
    Base.metadata.create_all(bind=engine)
    
    # Import password hasher inside init to prevent circular imports
    from ..security.auth import hash_password

    with SessionLocal() as db:
        # 1. Bootstrap default admin & analyst if not exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            default_admin_pass = os.environ.get("INITIAL_ADMIN_PASSWORD")
            if not default_admin_pass or len(default_admin_pass) < 12:
                raise RuntimeError(
                    "Set INITIAL_ADMIN_PASSWORD to a unique password of at least 12 characters "
                    "before initializing a new database."
                )
            db.add(User(
                username="admin",
                password_hash=hash_password(default_admin_pass),
                role="admin"
            ))

        analyst_user = db.query(User).filter(User.username == "analyst").first()
        analyst_password = os.environ.get("INITIAL_ANALYST_PASSWORD")
        if not analyst_user and analyst_password:
            if len(analyst_password) < 12:
                raise RuntimeError("INITIAL_ANALYST_PASSWORD must contain at least 12 characters.")
            db.add(User(
                username="analyst",
                password_hash=hash_password(analyst_password),
                role="analyst"
            ))

        # 2. Bootstrap default decoy sensors
        default_sensors = [
            Sensor(id="sensor-http-gateway", name="Decoy HTTP Gateway", sensor_type="http_gateway", host="127.0.0.1", port=8080, status="ACTIVE"),
            Sensor(id="sensor-ssh-bastion", name="Decoy SSH Bastion", sensor_type="ssh_bastion", host="127.0.0.1", port=2222, status="ACTIVE"),
            Sensor(id="sensor-canary-fs", name="Filesystem Canary Watcher", sensor_type="canary_fs", host="127.0.0.1", port=0, status="ACTIVE"),
        ]
        for s in default_sensors:
            if not db.query(Sensor).filter(Sensor.id == s.id).first():
                db.add(s)

        # 3. Bootstrap default decoys / honeytokens
        default_decoys = [
            Decoy(
                id="decoy-stripe-api",
                name="Production Stripe Live Gateway",
                decoy_type="api_key",
                target_service="Stripe API Gateway",
                token_id="qtok_stripe_live_prod",
                secret_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                status="ARMED"
            ),
            Decoy(
                id="decoy-postgres-cluster",
                name="Financial Core Postgres Database",
                decoy_type="database",
                target_service="Core Financial Postgres",
                token_id="qtok_db_postgres_main",
                secret_hash="a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e",
                status="ARMED"
            ),
            Decoy(
                id="decoy-aws-iam",
                name="AWS S3 Backup Operator Credentials",
                decoy_type="aws_iam",
                target_service="AWS IAM Cloud Metadata",
                token_id="qtok_aws_iam_backup",
                secret_hash="2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
                status="ARMED"
            ),
            Decoy(
                id="decoy-ssh-bastion-key",
                name="Bastion Host Root SSH Key",
                decoy_type="ssh_key",
                target_service="Decoy Bastion Vault",
                token_id="qtok_ssh_bastion_root",
                secret_hash="fcde2b2edba56bf408601fb721fe9b5c338d10ee429ea04fae5511b68fbf8fb9",
                status="ARMED"
            )
        ]
        for d in default_decoys:
            if not db.query(Decoy).filter(Decoy.id == d.id).first():
                db.add(d)

        db.commit()
