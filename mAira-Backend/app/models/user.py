"""SQLAlchemy Model for sch_con.tb_con_user."""

from sqlalchemy import BigInteger, Column, DateTime, String, Text, func
from app.models.base import Base


class User(Base):
    """User account model for students and faculty."""

    __tablename__ = "tb_con_user"

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    user_type = Column(String(20), nullable=False)  # STUDENT, FACULTY
    password_hash = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, INACTIVE, LOCKED
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    def __repr__(self) -> str:
        return f"<User id={self.user_id} email={self.email} type={self.user_type} status={self.status}>"
