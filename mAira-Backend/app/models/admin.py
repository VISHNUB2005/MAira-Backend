"""SQLAlchemy Model for sch_con.tb_con_admin."""

from sqlalchemy import BigInteger, Column, DateTime, String, Text, func
from app.models.base import Base


class Admin(Base):
    """Administrator account model."""

    __tablename__ = "tb_con_admin"

    admin_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Admin id={self.admin_id} email={self.email} status={self.status}>"
