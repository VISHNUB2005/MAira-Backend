"""SQLAlchemy Declarative Base."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Schema name in mira_db is sch_con
metadata = MetaData(schema="sch_con")


class Base(DeclarativeBase):
    """Base declarative model."""
    metadata = metadata
