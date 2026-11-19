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

# Create DB tables automatically if engine is available
if engine is not None:
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[DB] Table creation pending or skipped: {e}")

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
    history: list[dict] = []

@app.get("/api/health")
def health_check():
    has_db = bool(os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL"))
    return {
        "status": "healthy",
        "database": "Cloud Active" if has_db else "Configuring Cloud Ledger",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
    }

@app.get("/api/summary")
def get_summary(db: Session = Depends(get_db)):
    try:
        # Clean up any accidentally stored non-expense strings if any
        db.query(models.Expense).filter(models.Expense.item.ilike("%remember%")).delete()

        # Repair any previous typo records in DB (e.g. Yesterdat Milk Spent)
        typo_records = db.query(models.Expense).filter(models.Expense.item.ilike("%yesterdat%")).all()
        if typo_records:
            yesterday_date = date.today() - timedelta(days=1)
            yesterday_dt = datetime.combine(yesterday_date, datetime.now().time())
            for idx, rec in enumerate(typo_records):
                if idx == 0:
                    rec.item = "Milk"
                    rec.category = "Dairy"
                    rec.amount = 800.0
                    rec.expense_date = yesterday_date
                    rec.created_at = yesterday_dt
                else:
                    db.delete(rec)
        db.commit()

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
        memories_count = db.query(models.UserMemory).count()

        return {
            "today_total": float(today_sum or 0.0),
            "future_total": float(future_sum or 0.0),
            "total_records": total_records,
            "future_records": future_records,
            "memories_count": memories_count,
            "database": "Cloud Active"
        }
    except Exception as e:
        return {
            "today_total": 0.0,
            "future_total": 0.0,
            "total_records": 0,
            "future_records": 0,
            "memories_count": 0,
            "database": "Configuring Cloud Ledger",
            "note": f"Database connecting: {str(e)[:80]}"
        }

@app.get("/api/memories")
def get_all_memories(db: Session = Depends(get_db)):
    """Returns all remembered user preferences, budgets, and financial profile notes."""
    try:
        memories = db.query(models.UserMemory).order_by(models.UserMemory.id.desc()).all()
        return [
            {
                "id": m.id,
                "topic": m.topic,
                "content": m.content,
                "memory_type": m.memory_type,
                "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else ""
            }
            for m in memories
        ]
    except Exception as e:
        return []

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        return agent.process_chat(req.message, db, history=req.history)
    except Exception as e:
        return {
            "reply": f"⚠️ **Connection Issue**: Could not connect to database ({str(e)[:100]}). Please check connection settings.",
            "chart": None,
            "suggestions": [
                {"question": "What did I spend today?", "tooltip": "Query today's total expenses"}
            ],
            "db_type": "Cloud"
        }

@app.post("/api/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    """Clears and seeds clean, realistic data perfect for interview presentation."""
    try:
        db.query(models.Expense).delete()
        db.query(models.FutureExpense).delete()

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

        target_future_1 = date.today() + timedelta(days=12)
        target_future_2 = date.today() + timedelta(days=25)
        demo_future = [
            models.FutureExpense(item="Annual Bike Insurance", category="Bills & Utilities", expected_amount=3800.0, target_date=target_future_1, status="PLANNED", notes="Annual renewal"),
            models.FutureExpense(item="Quarterly High-speed Wifi", category="Bills & Utilities", expected_amount=1499.0, target_date=target_future_2, status="PLANNED", notes="Broadband bill")
        ]
        for fut in demo_future:
            db.add(fut)

        db.commit()
        return {"message": "Demo data seeded successfully!"}
    except Exception as e:
        return {"message": f"Could not seed demo data: {str(e)[:100]}"}

@app.post("/api/clear")
def clear_all_data(db: Session = Depends(get_db)):
    """Wipes all records so user can start from an empty clean state."""
    try:
        db.query(models.Expense).delete()
        db.query(models.FutureExpense).delete()
        db.commit()
        return {"message": "All expense records cleared."}
    except Exception as e:
        return {"message": f"Could not clear: {str(e)[:100]}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
