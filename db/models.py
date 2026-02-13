"""
Database models for the finance application.
"""
import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, 
    DateTime, Date, Text, ForeignKey, JSON, Enum, Numeric, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class ProvinceEnum(enum.Enum):
    AB = "AB"
    BC = "BC"
    MB = "MB"
    NB = "NB"
    NL = "NL"
    NS = "NS"
    NT = "NT"
    NU = "NU"
    ON = "ON"
    PE = "PE"
    QC = "QC"
    SK = "SK"
    YT = "YT"


class PayScheduleEnum(enum.Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"
    MONTHLY = "monthly"


class EnvelopeCategoryEnum(enum.Enum):
    BILLS = "bills"
    DEBT = "debt"
    SINKING = "sinking"
    SAVINGS = "savings"
    INVESTING = "investing"
    DISCRETIONARY = "discretionary"


class BillTypeEnum(enum.Enum):
    FIXED = "fixed"
    VARIABLE = "variable"
    SUBSCRIPTION = "subscription"


class RecurrenceEnum(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class DebtStrategyEnum(enum.Enum):
    AVALANCHE = "avalanche"
    SNOWBALL = "snowball"


class User(Base):
    """User account."""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    province = Column(Enum(ProvinceEnum), nullable=False)
    tax_year = Column(Integer, nullable=False, default=2024)
    pay_schedule = Column(Enum(PayScheduleEnum), nullable=False, default=PayScheduleEnum.BIWEEKLY)
    next_payday = Column(Date, nullable=True)  # Added for pay schedule
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    settings = Column(JSON, nullable=False, default=dict)
    meta_data = Column(JSON, nullable=False, default=dict)  # Changed from 'metadata' to 'meta_data'
    
    # Relationships
    income_streams = relationship("IncomeStream", back_populates="user", cascade="all, delete-orphan")
    envelopes = relationship("Envelope", back_populates="user", cascade="all, delete-orphan")
    bills = relationship("Bill", back_populates="user", cascade="all, delete-orphan")
    bill_occurrences = relationship("BillOccurrence", back_populates="user", cascade="all, delete-orphan")
    debts = relationship("Debt", back_populates="user", cascade="all, delete-orphan")
    sinking_funds = relationship("SinkingFund", back_populates="user", cascade="all, delete-orphan")
    savings_goals = relationship("SavingsGoal", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    paychecks = relationship("Paycheck", back_populates="user", cascade="all, delete-orphan")
    paycheque_windows = relationship("PaychequeWindow", back_populates="user", cascade="all, delete-orphan")


class IncomeStream(Base):
    """Income source for a user."""
    __tablename__ = "income_streams"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # salary, overtime, bonus, irregular, reimbursement
    gross_amount = Column(Numeric(12, 2), nullable=False)
    frequency = Column(Enum(PayScheduleEnum), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    deductions = Column(JSON, nullable=False, default=dict)  # RRSP, union, benefits, etc.
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    meta_data = Column(JSON, nullable=False, default=dict)  # Changed from 'metadata' to 'meta_data'
    
    # Relationships
    user = relationship("User", back_populates="income_streams")


class Envelope(Base):
    """Budget envelope for allocating funds."""
    __tablename__ = "envelopes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    category = Column(Enum(EnvelopeCategoryEnum), nullable=False)
    name = Column(String(100), nullable=False)
    target_amount = Column(Numeric(12, 2), nullable=False, default=0)
    current_balance = Column(Numeric(12, 2), nullable=False, default=0)
    priority = Column(Integer, nullable=False, default=5)
    due_date = Column(Date, nullable=True)
    recurrence = Column(Enum(RecurrenceEnum), nullable=True)
    auto_pay = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    meta_data = Column(JSON, nullable=False, default=dict)  # Changed from 'metadata' to 'meta_data'
    
    # Relationships
    user = relationship("User", back_populates="envelopes")
    bills = relationship("Bill", back_populates="envelope")
    debts = relationship("Debt", back_populates="envelope")
    sinking_funds = relationship("SinkingFund", back_populates="envelope")
    savings_goals = relationship("SavingsGoal", back_populates="envelope")
    transactions = relationship("Transaction", back_populates="envelope")


class Bill(Base):
    """Bill or recurring expense."""
    __tablename__ = "bills"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    envelope_id = Column(String(36), ForeignKey("envelopes.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    bill_type = Column(Enum(BillTypeEnum), nullable=False)
    due_date = Column(Date, nullable=False)
    recurrence = Column(Enum(RecurrenceEnum), nullable=True)
    paid = Column(Boolean, nullable=False, default=False)
    paid_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    meta_data = Column(JSON, nullable=False, default=dict)  # Changed from 'metadata' to 'meta_data'
    
    # Relationships
    user = relationship("User", back_populates="bills")
    envelope = relationship("Envelope", back_populates="bills")
    occurrences = relationship("BillOccurrence", back_populates="bill", cascade="all, delete-orphan")


class BillOccurrence(Base):
    """Individual occurrence of a bill for a specific paycheque window."""
    __tablename__ = "bill_occurrences"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    bill_id = Column(String(36), ForeignKey("bills.id"), nullable=False, index=True)
    paycheque_window_id = Column(String(36), ForeignKey("paycheque_windows.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    paid = Column(Boolean, nullable=False, default=False)
    paid_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    meta_data = Column(JSON, nullable=False, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="bill_occurrences")
    bill = relationship("Bill", back_populates="occurrences")
    paycheque_window = relationship("PaychequeWindow", back_populates="bill_occurrences")


class Debt(Base):
    """Debt account."""
    __tablename__ = "debts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    envelope_id = Column(String(36), ForeignKey("envelopes.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    balance = Column(Numeric(12, 2), nullable=False)
    apr = Column(Numeric(5, 4), nullable=False)  # 0.0000 to 1.0000
    minimum_payment = Column(Numeric(12, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    strategy = Column(Enum(DebtStrategyEnum), nullable=False, default=DebtStrategyEnum.AVALANCHE)
    paid_off = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    meta_data = Column(JSON, nullable=False, default=dict)  # Changed from 'metadata' to 'meta_data'
    
    # Relationships
    user = relationship("User", back_populates="debts")
    envelope = relationship("Envelope", back_populates="debts")


class SinkingFund(Base):
    """Sinking fund for future expenses."""
    __tablename__ = "sinking_funds"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    envelope_id = Column(String(36), ForeignKey("envelopes.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    target_amount = Column(Numeric(12, 2), nullable=False)
    current_balance = Column(Numeric(12, 2), nullable=False, default=0)
    deadline = Column(Date, nullable=False)
    monthly_contribution = Column(Numeric(12, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    meta_data = Column(JSON, nullable=False, default=dict)  # Changed from 'metadata' to 'meta_data'
    
    # Relationships
    user = relationship("User", back_populates="sinking_funds")
    envelope = relationship("Envelope", back_populates="sinking_funds")


class SavingsGoal(Base):
    """Savings or investing goal."""
    __tablename__ = "savings_goals"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    envelope_id = Column(String(36), ForeignKey("envelopes.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    target_amount = Column(Numeric(12, 2), nullable=False)
    current_balance = Column(Numeric(12, 2), nullable=False, default=0)
    target_date = Column(Date, nullable=True)
    monthly_contribution = Column(Numeric(12, 2), nullable=False, default=0)
    investment_strategy = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    meta_data = Column(JSON, nullable=False, default=dict)  # Changed from 'metadata' to 'meta_data'
    
    # Relationships
    user = relationship("User", back_populates="savings_goals")
    envelope = relationship("Envelope", back_populates="savings_goals")


class Transaction(Base):
    """Financial transaction."""
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    envelope_id = Column(String(36), ForeignKey("envelopes.id"), nullable=True, index=True)
    date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    merchant = Column(String(100), nullable=True)
    transaction_type = Column(String(50), nullable=False)  # income, expense, transfer
    split = Column(Boolean, nullable=False, default=False)
    parent_transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)
    imported = Column(Boolean, nullable=False, default=False)
    import_source = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    meta_data = Column(JSON, nullable=False, default=dict)  # Changed from 'metadata' to 'meta_data'
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    envelope = relationship("Envelope", back_populates="transactions")
    parent = relationship("Transaction", remote_side=[id], backref="splits")


class Paycheck(Base):
    """Paycheck record."""
    __tablename__ = "paychecks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    gross_amount = Column(Numeric(12, 2), nullable=False)
    net_amount = Column(Numeric(12, 2), nullable=False)
    federal_tax = Column(Numeric(12, 2), nullable=False)
    provincial_tax = Column(Numeric(12, 2), nullable=False)
    cpp_contribution = Column(Numeric(12, 2), nullable=False)
    ei_contribution = Column(Numeric(12, 2), nullable=False)
    qpp_contribution = Column(Numeric(12, 2), nullable=True)
    qpip_contribution = Column(Numeric(12, 2), nullable=True)
    other_deductions = Column(JSON, nullable=False, default=dict)
    allocations = Column(JSON, nullable=False, default=dict)  # envelope_id -> amount
    remaining_amount = Column(Numeric(12, 2), nullable=False, default=0)
    applied = Column(Boolean, nullable=False, default=False)
    applied_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    meta_data = Column(JSON, nullable=False, default=dict)  # Changed from 'metadata' to 'meta_data'
    
    # Relationships
    user = relationship("User", back_populates="paychecks")


class PaychequeWindow(Base):
    """Window between paycheques for bill assignment."""
    __tablename__ = "paycheque_windows"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    paycheck_id = Column(String(36), ForeignKey("paychecks.id"), nullable=True, index=True)
    total_bills = Column(Numeric(12, 2), nullable=False, default=0)
    total_allocated = Column(Numeric(12, 2), nullable=False, default=0)
    remaining_budget = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String(20), nullable=False, default="pending")  # pending, active, completed, archived
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    meta_data = Column(JSON, nullable=False, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="paycheque_windows")
    paycheck = relationship("Paycheck")
    bill_occurrences = relationship("BillOccurrence", back_populates="paycheque_window", cascade="all, delete-orphan")


class TaxTable(Base):
    """Stored tax table data."""
    __tablename__ = "tax_tables"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    year = Column(Integer, nullable=False, index=True)
    jurisdiction = Column(String(10), nullable=False, index=True)  # 'federal' or province code
    data = Column(JSON, nullable=False)
    source = Column(String(255), nullable=True)
    citation = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    meta_data = Column(JSON, nullable=False, default=dict)  # Changed from 'metadata' to 'meta_data'
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('year', 'jurisdiction', name='unique_year_jurisdiction'),)


class Database:
    """Database manager."""
    
    def __init__(self, database_url: str = "sqlite:///finance.db"):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def init_db(self):
        """Initialize database tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def close_session(self, session: Session):
        """Close database session."""
        session.close()


# Default database instance
default_db = Database()