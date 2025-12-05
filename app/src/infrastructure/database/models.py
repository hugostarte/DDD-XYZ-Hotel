

from sqlalchemy import Column, Integer, String, Boolean, DateTime, NUMERIC, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .connection import Base


class CustomerModel(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone_number = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    wallets = relationship("WalletModel", back_populates="customer", cascade="all, delete-orphan")
    bookings = relationship("BookingModel", back_populates="customer", cascade="all, delete-orphan")


class WalletModel(Base):
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    balance_amount = Column(NUMERIC(10, 2), default=0.00)
    balance_currency = Column(String(3), default="EUR")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    customer = relationship("CustomerModel", back_populates="wallets")
    transactions = relationship("TransactionModel", back_populates="wallet", cascade="all, delete-orphan")


class TransactionModel(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    amount = Column(NUMERIC(10, 2), nullable=False)
    currency = Column(String(3), default="EUR")
    transaction_type = Column(String(10), nullable=False)  # CREDIT/DEBIT
    reason = Column(Text, nullable=False)
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    wallet = relationship("WalletModel", back_populates="transactions")


class BookingModel(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    room_type = Column(String(20), nullable=False)  # STANDARD/SUPERIOR/SUITE
    room_quantity = Column(Integer, nullable=False)
    check_in_date = Column(DateTime(timezone=True), nullable=False)
    check_out_date = Column(DateTime(timezone=True), nullable=False)
    total_amount = Column(NUMERIC(10, 2), nullable=False)
    deposit_amount = Column(NUMERIC(10, 2), nullable=False)
    balance_amount = Column(NUMERIC(10, 2), nullable=False)
    status = Column(String(20), default="PENDING")  # PENDING/CONFIRMED/CANCELLED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    customer = relationship("CustomerModel", back_populates="bookings")
    payments = relationship("PaymentModel", back_populates="booking", cascade="all, delete-orphan")


class PaymentModel(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    amount = Column(NUMERIC(10, 2), nullable=False)
    payment_type = Column(String(10), nullable=False)  # DEPOSIT/BALANCE
    is_processed = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    booking = relationship("BookingModel", back_populates="payments")


class AdministratorModel(Base):
    __tablename__ = "administrators"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(String(50), default="admin")
    created_at = Column(DateTime(timezone=True), server_default=func.now())