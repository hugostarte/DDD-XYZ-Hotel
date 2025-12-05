"""
Configuration de la base de données PostgreSQL.
Connexion et session SQLAlchemy.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://hotel_user:hotel_password@localhost:5432/xyz_hotel"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_database_session():
    """Créer une session de base de données."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()