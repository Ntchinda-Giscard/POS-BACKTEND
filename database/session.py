# database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


LOCAL_DB_PATH = r"C:\poswaza\temp\db"

# 1) Point to your SQLite file (relative to working dir)
os.makedirs(LOCAL_DB_PATH, exist_ok=True)
SQLALCHEMY_DATABASE_URL = rf"sqlite:///{LOCAL_DB_PATH}\pos_local.db"

# 2) For SQLite only, we need this argument
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3) session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# 4) Base class for your ORM models
Base = declarative_base()

# 5) Dependency function to inject DB sessions into FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
