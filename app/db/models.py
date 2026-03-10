# app/db/models.py

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class Family(Base):
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    twilio_whatsapp_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="family", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="family", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    family = relationship("Family", back_populates="users")
    transactions = relationship("Transaction", back_populates="user")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    original_text = Column(String, nullable=True)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)  # expense / income
    category = Column(String, nullable=False)

    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_phone = Column(String, nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    family = relationship("Family", back_populates="transactions")
    user = relationship("User", back_populates="transactions")