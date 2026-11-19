from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, Text, DateTime
from database import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    item = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False, default="General")
    amount = Column(Float, nullable=False)
    expense_date = Column(Date, default=date.today, index=True)
    raw_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class FutureExpense(Base):
    __tablename__ = "future_expenses"

    id = Column(Integer, primary_key=True, index=True)
    item = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False, default="Future")
    expected_amount = Column(Float, nullable=False)
    target_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), default="PLANNED")  # PLANNED, COMPLETED, CANCELLED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True, index=True)
    memory_type = Column(String(50), default="PREFERENCE")  # BUDGET, RECURRING_BILL, PREFERENCE, INCOME, GOAL, NOTE
    topic = Column(String(100), nullable=False, index=True) # e.g. "Grocery Budget", "Monthly Salary"
    content = Column(Text, nullable=False)                  # e.g. "Monthly grocery budget is ₹8,000"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
