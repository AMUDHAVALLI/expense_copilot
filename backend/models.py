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

