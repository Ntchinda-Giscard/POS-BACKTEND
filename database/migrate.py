"""Additive schema upgrades for the local config database (create_all never alters existing tables)."""
import logging
from sqlalchemy import inspect, text
from .session import Base, engine
from . import models  # noqa: F401  (registers every table on Base before create_all)

logger = logging.getLogger(__name__)


def upgrade():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column.type.compile(engine.dialect)}'
                logger.info(f"migrate: {ddl}")
                conn.execute(text(ddl))
