# Import everything from database.py to maintain backward compatibility
from .database import (
    engine,
    SessionLocal,
    Base,
    get_db,
    DATABASE_URL
)

__all__ = ['engine', 'SessionLocal', 'Base', 'get_db', 'DATABASE_URL']

