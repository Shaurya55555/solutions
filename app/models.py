# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Index
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
import datetime

from app.database import Base

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)

    transactions = relationship("Transaction", back_populates="merchant")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="INR")
    status = Column(String, nullable=False, index=True) # e.g., initiated, processed, failed, settled
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    merchant = relationship("Merchant", back_populates="transactions")
    events = relationship("Event", back_populates="transaction", order_by="Event.timestamp")

class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, index=True) # event_id to ensure strict idempotency
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)

    transaction = relationship("Transaction", back_populates="events")

# Add composite indexes if necessary, though single indexes cover most basic filtering
Index('idx_transaction_status_merchant', Transaction.status, Transaction.merchant_id)
