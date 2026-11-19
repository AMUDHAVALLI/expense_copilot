import os
from datetime import date, timedelta
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import engine, get_db, Base, db_type
import models
import agent

# Create DB tables automatically
if engine is not None:
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[DB] Table creation skipped or pending connection: {e}")

app = FastAPI(title="Expense Copilot Enterprise API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "database": db_type,
        "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
    }

@app.get("/api/summary")
def get_summary(db: Session = Depends(get_db)):
    today_sum = (
        db.query(func.coalesce(func.sum(models.Expense.amount), 0.0))
        .filter(models.Expense.expense_date == date.today())
        .scalar()
    )
    future_sum = (
        db.query(func.coalesce(func.sum(models.FutureExpense.expected_amount), 0.0))
        .filter(models.FutureExpense.status == "PLANNED")
        .scalar()
    )
    total_records = db.query(models.Expense).count()
    future_records = db.query(models.FutureExpense).count()

    return {
        "today_total": float(today_sum),
        "future_total": float(future_sum),
        "total_records": total_records,
        "future_records": future_records,
        "database": db_type
    }

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    return agent.process_chat(req.message, db)

@app.post("/api/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    """Clears and seeds clean, realistic data perfect for interview presentation."""
    db.query(models.Expense).delete()
    db.query(models.FutureExpense).delete()

    # Clean realistic demo records
    demo_expenses = [
        models.Expense(item="Milk (2L)", category="Dairy", amount=64.0, expense_date=date.today(), raw_message="Milk 64"),
        models.Expense(item="Paneer & Curd", category="Dairy", amount=120.0, expense_date=date.today(), raw_message="Paneer and curd 120"),
        models.Expense(item="Fresh Vegetables", category="Vegetables & Groceries", amount=185.0, expense_date=date.today(), raw_message="Veggies 185"),
        models.Expense(item="Whole Wheat Bread", category="General", amount=45.0, expense_date=date.today(), raw_message="Bread 45"),
        models.Expense(item="Cold Coffee & Sandwich", category="Food & Dining", amount=160.0, expense_date=date.today(), raw_message="Coffee sandwich 160"),
        models.Expense(item="Petrol", category="Transport", amount=350.0, expense_date=date.today(), raw_message="Petrol 350")
    ]
    for exp in demo_expenses:
        db.add(exp)

    # Future planned commitments
    target_future_1 = date.today() + timedelta(days=12)
    target_future_2 = date.today() + timedelta(days=25)
    demo_future = [
        models.FutureExpense(item="Annual Bike Insurance", category="Bills & Utilities", expected_amount=3800.0, target_date=target_future_1, status="PLANNED", notes="Annual renewal"),
        models.FutureExpense(item="Quarterly High-speed Wifi", category="Bills & Utilities", expected_amount=1499.0, target_date=target_future_2, status="PLANNED", notes="Broadband bill")
    ]
    for fut in demo_future:
        db.add(fut)

    db.commit()
    return {"message": "Demo data seeded successfully in PostgreSQL!"}

@app.post("/api/clear")
def clear_all_data(db: Session = Depends(get_db)):
    """Wipes all records so user can start from an empty clean state."""
    db.query(models.Expense).delete()
    db.query(models.FutureExpense).delete()
    db.commit()
    return {"message": "All expense records cleared from PostgreSQL."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
