from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Float
from datetime import datetime
from sqlalchemy.orm import relationship

from app.db.database import Base


class Family(Base):
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    dashboard_title = Column(String, nullable=False, default="כלכלת הבית")

    users = relationship("User", back_populates="family", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="family", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True, index=True)

    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)

    is_admin = Column(Boolean, default=False, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    family = relationship("Family", back_populates="users")
    transactions = relationship("Transaction", back_populates="user")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    original_text = Column(String, nullable=True)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)
    category = Column(String, nullable=False)

    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_phone = Column(String, nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    family = relationship("Family", back_populates="transactions")
    user = relationship("User", back_populates="transactions")


class JoinRequest(Base):
    __tablename__ = "join_requests"

    id = Column(Integer, primary_key=True, index=True)
    requester_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requester_phone = Column(String, nullable=False)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class MerchantMemory(Base):
    __tablename__ = "merchant_memories"

    id = Column(Integer, primary_key=True, index=True)

    scope_type = Column(String, nullable=False)  # user / family / global
    scope_id = Column(Integer, nullable=True)    # user_id / family_id / None

    merchant_key = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False)
    tx_type = Column(String, nullable=False)  # expense / income

    count = Column(Integer, default=1, nullable=False)
    last_used_at = Column(DateTime, default=datetime.utcnow, nullable=False)