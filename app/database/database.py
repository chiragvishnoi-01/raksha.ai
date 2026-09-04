"""RAKSHA AI - Database Connection & Session Management"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database.models import Base

logger = logging.getLogger("raksha.database")

def get_engine():
    """Attempts to connect to configured DATABASE_URL (PostgreSQL).
    Falls back gracefully to SQLite if PostgreSQL connection fails.
    """
    db_url = settings.DATABASE_URL
    try:
        if "postgresql" in db_url:
            # Test PostgreSQL connection with a short timeout
            engine = create_engine(db_url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
            with engine.connect():
                logger.info("Connected successfully to PostgreSQL database.")
                return engine
    except Exception as e:
        logger.warning(f"PostgreSQL connection to {db_url} failed ({e}). Falling back to local SQLite database.")
    
    # SQLite Fallback
    fallback_url = "sqlite:///./raksha.db"
    engine = create_engine(fallback_url, connect_args={"check_same_thread": False})
    logger.info("Using local SQLite database: ./raksha.db")
    return engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes tables if they do not exist."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized.")

def get_db():
    """FastAPI Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
