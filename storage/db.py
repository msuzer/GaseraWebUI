# storage/db.py
from __future__ import annotations
import os, pathlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# SQLite by default → ./data/gasera.db (override with GASERA_DB_URL)
DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_SQLITE = f"sqlite:///{DATA_DIR / 'gasera.db'}"
DB_URL = os.environ.get("GASERA_DB_URL", DEFAULT_SQLITE)

connect_args = {}
if DB_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False   # Flask + background thread safe

engine = create_engine(DB_URL, pool_pre_ping=True, future=True, connect_args=connect_args)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))

def get_session():
    return SessionLocal()

def remove_session():
    SessionLocal.remove()
