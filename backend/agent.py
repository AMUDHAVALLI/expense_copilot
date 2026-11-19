import json
import os
import re
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from dotenv import load_dotenv

import models

# Load .env from backend directory as well as root
env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_file)
load_dotenv()

_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=_api_key, timeout=5.0) if _api_key else None

CATEGORIES = [
    "Dairy",
    "Vegetables & Groceries",
    "Food & Dining",
    "Transport",
    "Bills & Utilities",
    "Loans & EMI",
    "Education & Fees",
    "Health & Fitness",
    "Shopping",
    "Entertainment",
    "General"
]

SYSTEM_PROMPT = f"""
You are an intelligent Expense Copilot AI Assistant.
Today's local date is: {date.today().strftime('%Y-%m-%d')} ({date.today().strftime('%A')}).
All data is stored and retrieved strictly from your secure financial ledger.

Known Categories:
- "Dairy" (Milk, curd, cheese, paneer, butter, ghee, yogurt, etc.)
- "Vegetables & Groceries" (Vegetables, groceries, fruits, onion, tomato, potato, provisions, etc.)
- "Food & Dining" (Breakfast, lunch, dinner, snacks, tea, coffee, Swiggy, Zomato, restaurant, etc.)
- "Transport" (Petrol, diesel, fuel, cab, auto, bus, train, toll, etc.)
- "Bills & Utilities" (Electricity, wifi, recharge, rent, gas, maid, maintenance, etc.)
- "Loans & EMI" (Personal loan, home loan, car loan, EMI, interest, etc.)
- "Education & Fees" (School fees, college fees, tuition, courses, books, etc.)
- "Health & Fitness" (Supplements, protein, doctor, medicines, pharmacy, gym, etc.)
- "Entertainment" (Movies, games, subscriptions, etc.)
- "General" (Misc items)

IMPORTANT RULES FOR ADDING EXPENSES:
1. When a user provides a list of multiple expenses (e.g. separated by commas, 'and', 'for rs', etc.), you MUST extract EVERY SINGLE ITEM. Do NOT stop after the first item!
2. Date Detection:
   - If user says 'last month', set expense_date to a date in the previous month (YYYY-MM-DD).
   - If user says 'yesterday', set expense_date to yesterday.
   - Otherwise default to today's date.
3. Chart Rule:
   - "wants_chart": true ONLY if the user explicitly used words like 'chart', 'graph', 'pie', 'bar', 'plot', 'visualize', OR if asking for "PREDICT_EXPENSES" (forecasting always benefits from a chart).
4. Prediction Rule:
   - If user asks to predict, forecast, project future expenses (e.g. 'Predict my next month expense', 'forecast my spend', 'predict future expenses'):
     Set "intent": "PREDICT_EXPENSES", "wants_chart": true, "recommended_chart": "bar".
5. Memory Rules:
   - "REMEMBER": If user asks to remember a financial preference, budget, salary, or habit (e.g. "Remember that my grocery budget is ₹8000", "Remember salary is 65k", "Note that car EMI is on the 5th"):
     Set "intent": "REMEMBER", and provide "memory": {{"topic": "Grocery Budget", "content": "Monthly grocery budget is ₹8000", "memory_type": "BUDGET"}}.
   - "RECALL_MEMORY": If user asks what you remember (e.g. "What do you remember about my finances?", "Show my financial profile", "What is my grocery budget?"):
     Set "intent": "RECALL_MEMORY".
   - "FORGET_MEMORY": If user asks to forget or clear memories (e.g. "Forget my grocery budget", "Clear memories"):
     Set "intent": "FORGET_MEMORY", "topic_target": "Grocery Budget" | "ALL".

Respond strictly in valid JSON matching this schema:
{{
  "intent": "ADD_TODAY_EXPENSE" | "ADD_FUTURE_EXPENSE" | "QUERY_EXPENSES" | "PREDICT_EXPENSES" | "REMEMBER" | "RECALL_MEMORY" | "FORGET_MEMORY" | "GENERAL",
  "expense_date": "YYYY-MM-DD" | null,
  "items": [
    {{"item": "Milk", "category": "Dairy", "amount": 500.0}},
    {{"item": "Personal Loan", "category": "Loans & EMI", "amount": 20.0}}
  ],
  "future_item": {{"item": "Bike Service", "category": "Bills & Utilities", "expected_amount": 3500.0, "target_date": "YYYY-MM-DD"}},
  "memory": {{"topic": "Grocery Budget", "content": "Monthly grocery budget is ₹8000", "memory_type": "BUDGET"}},
  "topic_target": "Grocery Budget" | "ALL" | null,
  "time_filter": "TODAY" | "FUTURE" | "ALL_TIME",
  "target_category": "Dairy" | null,
  "target_item": "Milk" | null,
  "wants_chart": true | false,
  "recommended_chart": "pie" | "bar" | "line" | null,
  "reply_text": "Friendly preliminary text"
}}
"""

def user_explicitly_wants_chart(text: str) -> bool:
    """Returns True ONLY if user explicitly asked for a chart or visualization."""
    chart_keywords = [r'\bchart\b', r'\bgraph\b', r'\bpie\b', r'\bbar\b', r'\bline\b', r'\bplot\b', r'\bvisual', r'\bvisualize\b']
    pattern = '|'.join(chart_keywords)
    return bool(re.search(pattern, text, flags=re.I))

def detect_category(text: str) -> str:
    n = text.lower()
    if any(w in n for w in ['loan', 'emi', 'mortgage', 'debt']):
        return 'Loans & EMI'
    if any(w in n for w in ['fee', 'fees', 'school', 'college', 'tuition', 'education']):
        return 'Education & Fees'
    if any(w in n for w in ['supplement', 'protein', 'medicine', 'doctor', 'hospital', 'pharma', 'gym', 'fitness']):
        return 'Health & Fitness'
    if any(w in n for w in ['dairy', 'milk', 'curd', 'cheese', 'paneer', 'butter', 'ghee', 'yogurt']):
        return 'Dairy'
    if any(w in n for w in ['vegetable', 'veggie', 'veg', 'grocery', 'groceries', 'onion', 'tomato', 'potato', 'fruit', 'apple']):
        return 'Vegetables & Groceries'
    if any(w in n for w in ['snack', 'food', 'coffee', 'tea', 'dinner', 'lunch', 'breakfast', 'restaurant', 'burger', 'pizza']):
        return 'Food & Dining'
    if any(w in n for w in ['petrol', 'diesel', 'fuel', 'cab', 'uber', 'ola', 'auto', 'bus', 'train', 'metro', 'toll', 'travel']):
        return 'Transport'
    if any(w in n for w in ['bill', 'recharge', 'wifi', 'electricity', 'rent', 'water', 'gas', 'maid']):
        return 'Bills & Utilities'
    if any(w in n for w in ['movie', 'game', 'netflix', 'prime', 'hotstar']):
        return 'Entertainment'
    return 'General'

def extract_target_filter(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extracts target category and target item from a query string."""
    text_lower = text.lower()
    target_category = None
    target_item = None

    if any(w in text_lower for w in ["loan", "emi"]):
        target_category = "Loans & EMI"
    elif any(w in text_lower for w in ["fee", "school", "education"]):
        target_category = "Education & Fees"
    elif any(w in text_lower for w in ["dairy", "milk", "cheese", "paneer", "curd"]):
        target_category = "Dairy"
        if "milk" in text_lower:
            target_item = "milk"
    elif any(w in text_lower for w in ["vegetable", "veggie", "veg", "grocery", "groceries"]):
        target_category = "Vegetables & Groceries"
    elif any(w in text_lower for w in ["food", "snack", "dining", "restaurant"]):
        target_category = "Food & Dining"
    elif any(w in text_lower for w in ["petrol", "fuel", "transport", "travel"]):
        target_category = "Transport"
    elif any(w in text_lower for w in ["bill", "rent", "electricity"]):
        target_category = "Bills & Utilities"
    elif any(w in text_lower for w in ["supplement", "health", "medicine", "doctor"]):
        target_category = "Health & Fitness"

    return target_category, target_item

def parse_date_from_message(text: str) -> Tuple[date, datetime]:
    """
    Parses date and timestamp context from user message.
    Handles 'yesterday' and common typos ('yesterdat', 'yesteday', 'yesturday', 'yestarday', 'yest', etc.),
    'last month', 'N days ago', and explicit dates.
    Returns (target_date, target_datetime).
    """
    t = text.lower()
    now = datetime.now()

    # Yesterday & typos (yesterdat, yesteday, yesturday, yestarday, yest, etc.)
    if re.search(r'\b(yest[a-z]*|yesterdat|yesteday|yesturday|yestarday|yestrday)\b', t):
        yesterday_date = date.today() - timedelta(days=1)
        yesterday_datetime = now - timedelta(days=1)
        return yesterday_date, yesterday_datetime

    # N days ago (e.g. "2 days ago")
    m_days = re.search(r'(\d+)\s+days?\s+(?:ago|back|before)', t)
    if m_days:
        days_count = int(m_days.group(1))
        target_d = date.today() - timedelta(days=days_count)
        target_dt = now - timedelta(days=days_count)
        return target_d, target_dt

    # Last month
    if "last month" in t:
        first_of_this_month = date.today().replace(day=1)
        last_month_end = first_of_this_month - timedelta(days=1)
        target_d = last_month_end.replace(day=min(15, last_month_end.day))
        target_dt = datetime.combine(target_d, now.time())
        return target_d, target_dt

    return date.today(), now

def extract_all_expenses(text: str) -> List[Dict[str, Any]]:
    """
    Robust multi-strategy parser that splits lists by comma, 'and', semicolons,
    and extracts EVERY single expense item and amount without skipping any.
    """
    cleaned = text.strip()
    if cleaned.lower().startswith(("remember", "forget", "predict", "forecast", "what do", "how much", "calculate")):
        return []

    time_cleanup_pattern = r'\b(last\s+month|this\s+month|today|yesterday|yesterdat|yesteday|yesturday|yestarday|yestrday|yest)\b'

    # Normalize common connectors
    chunks = re.split(r'[,;\n]|(?:\band\b)', cleaned)
    items = []

    for chunk in chunks:
        c = chunk.strip()
        if not c:
            continue

        # Strip time keywords early
        c = re.sub(time_cleanup_pattern, '', c, flags=re.I).strip()
        
        # Remove leading boilerplate
        c = re.sub(r'^(?:i\s+)?(?:spent|bought|paid|gave|give|given)\s+', '', c, flags=re.I).strip()
        # Remove trailing boilerplate
        c = re.sub(r'\s+(?:i\s+have\s+given|given|i\s+gave)$', '', c, flags=re.I).strip()

        # Strategy 1: (rs|inr)? <amount> (rs|inr)? (for|on|of|spent on) <item>
        # e.g. "rs 500 for milk", "500 for milk"
        m1 = re.search(r'^(?:rs\.?|inr|₹|\$)?\s*(\d+(?:\.\d+)?)\s*(?:rs\.?|inr|₹|\$)?\s*(?:for|on|of|spent\s+on)?\s+([a-zA-Z\s]+)$', c, flags=re.I)
        if m1:
            itm = m1.group(2).strip()
            itm = re.sub(r'\b(spent|bought|paid|given)\b', '', itm, flags=re.I).strip().title()
            amt = float(m1.group(1))
            if itm and amt > 0:
                items.append({"item": itm, "category": detect_category(itm), "amount": amt})
                continue

        # Strategy 2: <item> (?:spent|bought|paid|for|on|of|is|:|-)? (rs|inr)? <amount> (rs|inr)?
        # e.g. "yesterdat milk spent 800", "milk spent 800", "milk 800", "perosonal loan for 20 rs"
        m2 = re.search(r'^([a-zA-Z\s]+?)\s*(?:spent|bought|paid|for|on|of|is|:|-)?\s*(?:rs\.?|inr|₹|\$)?\s*(\d+(?:\.\d+)?)\s*(?:rs\.?|inr|₹|\$)?$', c, flags=re.I)
        if m2:
            itm = m2.group(1).strip()
            itm = re.sub(r'\b(spent|bought|paid|given)\b', '', itm, flags=re.I).strip().title()
            amt = float(m2.group(2))
            if itm and amt > 0:
                items.append({"item": itm, "category": detect_category(itm), "amount": amt})
                continue

        # Strategy 3: Flexible fallback regex: find digits and words
        dm = re.search(r'(\d+(?:\.\d+)?)', c)
        if dm:
            amt = float(dm.group(1))
            itm = re.sub(r'\b(rs\.?|inr|for|on|of|spent|paid|bought|today|yesterday|yesterdat|yesteday|yest|last month|given)\b|[₹\$]', '', c, flags=re.I)
            itm = re.sub(r'\d+(?:\.\d+)?', '', itm).strip().title()
            if itm and amt > 0:
                items.append({"item": itm, "category": detect_category(itm), "amount": amt})

    return items

def heuristic_fallback_parse(user_message: str) -> Dict[str, Any]:
    """Smart parser when OpenAI is unavailable or for instant local fallback."""
    msg = user_message.strip()
    msg_lower = msg.lower()
    wants_chart = user_explicitly_wants_chart(msg)

    # 0. Future Prediction & Forecasting Intent
    prediction_keywords = ["predict", "prediction", "forecast", "forecasting", "projected", "projection", "future spend", "future prediction", "run rate", "burn rate", "estimate next month", "next month expense"]
    if any(k in msg_lower for k in prediction_keywords):
        target_cat, target_itm = extract_target_filter(msg)
        chart_type = "line" if ("line" in msg_lower or "trend" in msg_lower) else ("pie" if "pie" in msg_lower else "bar")
        return {
            "intent": "PREDICT_EXPENSES",
            "target_category": target_cat,
            "target_item": target_itm,
            "wants_chart": True,
            "recommended_chart": chart_type,
            "reply_text": ""
        }

    # 0B. Memory Intents (Remember, Recall, Forget)
    if any(k in msg_lower for k in ["forget", "delete memory", "clear memory", "remove memory", "reset memory"]):
        topic_target = re.sub(r'\b(forget|delete|clear|remove|reset|my|all|memories|memory|about)\b', '', msg, flags=re.I).strip()
        return {
            "intent": "FORGET_MEMORY",
            "topic_target": topic_target or "ALL",
            "wants_chart": False,
            "recommended_chart": None,
            "reply_text": ""
        }

    recall_phrases = ["what do you remember", "show memories", "show memory", "my memory", "financial profile", "remembered budget", "do you remember", "what are my memories", "my preferences", "show remembered", "list memories"]
    if any(k in msg_lower for k in recall_phrases):
        return {
            "intent": "RECALL_MEMORY",
            "wants_chart": False,
            "recommended_chart": None,
            "reply_text": ""
        }

    remember_triggers = ["remember that", "remember my", "remember to", "remember i", "remember", "note that", "keep in mind that", "keep track that"]
    starts_remember = any(msg_lower.startswith(t) for t in remember_triggers)
    is_budget_preference = bool(re.search(r'\b(my\s+budget|my\s+salary|salary\s+is|budget\s+is)\b', msg_lower))

    if starts_remember or is_budget_preference:
        clean_content = re.sub(r'^(?:remember\s+(?:that\s+|my\s+|to\s+|i\s+)?|note\s+that\s+|keep\s+in\s+mind\s+that\s+|keep\s+track\s+that\s+)', '', msg, flags=re.I).strip()
        topic = "General Financial Preference"
        mem_type = "PREFERENCE"
        if "budget" in msg_lower:
            topic = "Monthly Budget"
            mem_type = "BUDGET"
            if "grocery" in msg_lower or "groceries" in msg_lower:
                topic = "Grocery Budget"
            elif "dairy" in msg_lower or "milk" in msg_lower:
                topic = "Dairy Budget"
            elif "dining" in msg_lower or "food" in msg_lower:
                topic = "Dining Budget"
        elif "salary" in msg_lower or "income" in msg_lower:
            topic = "Monthly Salary"
            mem_type = "INCOME"
        elif any(k in msg_lower for k in ["emi", "loan", "rent", "bill", "due date"]):
            topic = "Recurring Commitment"
            mem_type = "RECURRING_BILL"

        return {
            "intent": "REMEMBER",
            "memory": {
                "topic": topic,
                "content": clean_content or msg,
                "memory_type": mem_type
            },
            "wants_chart": False,
            "recommended_chart": None,
            "reply_text": ""
        }

    # 1. Future Expense Intent
    future_keywords = ["plan", "future", "next month", "upcoming", "scheduled", "will spend", "planning"]
    if any(k in msg_lower for k in future_keywords) and re.search(r'\d+', msg_lower) and not re.search(r'(spent|bought|paid)', msg_lower):
        numbers = re.findall(r'(\d+(?:\.\d+)?)', msg)
        amount = float(numbers[0]) if numbers else 1000.0
        clean_item = re.sub(r'\b(plan|planning|to|spend|on|for|next|month|future|december|january|today|tomorrow|\d+(?:st|nd|rd|th)?)\b|[₹\$]', '', msg, flags=re.I).strip()
        clean_item = re.sub(r'\s+', ' ', clean_item).strip()
        if not clean_item:
            clean_item = "Planned Commitment"
        
        target_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
        return {
            "intent": "ADD_FUTURE_EXPENSE",
            "wants_chart": wants_chart,
            "recommended_chart": "bar" if wants_chart else None,
            "future_item": {
                "item": clean_item.title(),
                "category": detect_category(clean_item),
                "expected_amount": amount,
                "target_date": target_date
            },
            "reply_text": ""
        }

    # 2. Query / Calculate / Show Expenses
    query_keywords = ["calculate", "how much", "what did", "show", "chart", "total", "sum", "amount", "list", "report", "graph", "pie", "bar", "spent on"]
    is_query = (any(k in msg_lower for k in query_keywords) or wants_chart) and not re.search(r'(spent|bought|paid|given)\s+(?:rs|\d+)', msg_lower)

    if is_query:
        target_cat, target_itm = extract_target_filter(msg)
        time_filt = "FUTURE" if ("future" in msg_lower or "upcoming" in msg_lower) else (
            "YESTERDAY" if re.search(r'\b(yest[a-z]*|yesterdat|yesteday|yesturday|yest)\b', msg_lower) else (
                "TODAY" if "today" in msg_lower else "ALL_TIME"
            )
        )
        chart_type = "bar" if "bar" in msg_lower else ("line" if "line" in msg_lower else "pie")

        return {
            "intent": "QUERY_EXPENSES",
            "time_filter": time_filt,
            "target_category": target_cat,
            "target_item": target_itm,
            "wants_chart": wants_chart,
            "recommended_chart": chart_type if wants_chart else None,
            "reply_text": ""
        }

    # 3. Add Expenses (Extract ALL items)
    items = extract_all_expenses(msg)
    if items:
        target_d, _ = parse_date_from_message(msg)
        return {
            "intent": "ADD_TODAY_EXPENSE",
            "expense_date": target_d.strftime("%Y-%m-%d"),
            "wants_chart": wants_chart,
            "recommended_chart": "pie" if wants_chart else None,
            "items": items,
            "reply_text": ""
        }

    return {
        "intent": "GENERAL",
        "wants_chart": False,
        "recommended_chart": None,
        "reply_text": "I can help you track and calculate your expenses! Try entering your expenses (e.g. 'Milk 45, Bread 35') or asking questions."
    }

def process_chat(user_message: str, db: Session, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    data = None

    try:
        if not openai_client:
            raise ValueError("OpenAI client not configured")
        
        openai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            for h in history[-4:]:
                r = h.get("role")
                t = h.get("text") or h.get("content") or ""
                if r in ["user", "assistant"] and t:
                    openai_messages.append({"role": r, "content": t[:400]})
        openai_messages.append({"role": "user", "content": user_message})

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=openai_messages,
            temperature=0.0
        )
        data = json.loads(response.choices[0].message.content)
    except Exception:
        data = heuristic_fallback_parse(user_message)

    # Double-check: ensure NO items were dropped by LLM (only for expense entry intents)
    if data.get("intent") in ["ADD_TODAY_EXPENSE", "GENERAL"]:
        extracted_fallback = extract_all_expenses(user_message)
        if extracted_fallback and len(extracted_fallback) > len(data.get("items", [])):
            data["items"] = extracted_fallback
            data["intent"] = "ADD_TODAY_EXPENSE"

    explicit_chart = user_explicitly_wants_chart(user_message) or data.get("wants_chart", False)
    intent = data.get("intent", "GENERAL")
    chart_payload = None
    reply = ""

    target_category = data.get("target_category")
    target_item = data.get("target_item")

    # Multi-turn Context Resolution (resolves "it", "that", "again" from conversational history)
    if history and (not target_category and not target_item):
        msg_l = user_message.lower()
        is_contextual = any(k in msg_l for k in [" it", " that", " this", " those", "again", "for that", "show it", "show that"])
        if is_contextual:
            for past in reversed(history[-4:]):
                past_text = past.get("text", "") or past.get("content", "") or ""
                past_cat, past_item = extract_target_filter(past_text)
                if past_cat or past_item:
                    target_category = past_cat
                    target_item = past_item
                    break
    if not target_category:
        detected_cat, detected_item = extract_target_filter(user_message)
        if detected_cat:
            target_category = detected_cat
        if detected_item:
            target_item = detected_item

    # -------------------------------------------------------------
    # 1. ADD EXPENSES (Stores ALL extracted items in PostgreSQL)
    # -------------------------------------------------------------
    if intent == "ADD_TODAY_EXPENSE":
        items = data.get("items", [])
        saved_items = []
        total_amount = 0.0

        # Determine target date & timestamp
        target_date_val, target_datetime_val = parse_date_from_message(user_message)
        has_explicit_past = bool(re.search(r'\b(yest[a-z]*|yesterdat|yesteday|yesturday|days?\s+ago|last\s+month)\b', user_message.lower()))
        
        if not has_explicit_past and data.get("expense_date"):
            try:
                target_date_val = datetime.strptime(data["expense_date"], "%Y-%m-%d").date()
                target_datetime_val = datetime.combine(target_date_val, datetime.now().time())
            except Exception:
                pass

        for itm in items:
            amount = float(itm.get("amount", 0.0))
            if amount > 0:
                exp = models.Expense(
                    item=itm.get("item", "Misc"),
                    category=itm.get("category", detect_category(itm.get("item", ""))),
                    amount=amount,
                    expense_date=target_date_val,
                    created_at=target_datetime_val,
                    raw_message=user_message
                )
                db.add(exp)
                total_amount += amount
                saved_items.append(f"• **{exp.item}** ({exp.category}): ₹{amount:.2f}")
        db.commit()

        # Build chart ONLY if explicitly asked
        if explicit_chart:
            saved_cat_sums = (
                db.query(models.Expense.category, func.sum(models.Expense.amount))
                .filter(models.Expense.expense_date == target_date_val)
                .group_by(models.Expense.category)
                .all()
            )
            chart_payload = {
                "type": "pie",
                "title": f"Expense Breakdown ({target_date_val.strftime('%b %d, %Y')})",
                "data": [{"name": cat, "value": round(float(tot), 2)} for cat, tot in saved_cat_sums]
            }

        if target_date_val == date.today() - timedelta(days=1):
            date_label = f"Yesterday, {target_date_val.strftime('%b %d, %Y')}"
        elif "last month" in user_message.lower():
            date_label = "Last Month"
        else:
            date_label = target_date_val.strftime('%b %d, %Y')

        reply = (
            f"✅ Successfully recorded **{len(saved_items)} item(s)** ({date_label}):\n\n"
            + "\n".join(saved_items)
            + f"\n\n👉 **Total Recorded**: **₹{total_amount:.2f}**\n"
            f"📅 **Database Stored Date**: *{target_date_val.strftime('%A, %b %d, %Y')}*"
        )

    # -------------------------------------------------------------
    # 2. ADD FUTURE EXPENSE
    # -------------------------------------------------------------
    elif intent == "ADD_FUTURE_EXPENSE":
        f_item = data.get("future_item", {})
        expected_amount = float(f_item.get("expected_amount", 0.0))
        target_date_str = f_item.get("target_date")

        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except Exception:
            target_date = date.today() + timedelta(days=30)

        fut = models.FutureExpense(
            item=f_item.get("item", "Planned Expense"),
            category=f_item.get("category", "Bills & Utilities"),
            expected_amount=expected_amount,
            target_date=target_date,
            status="PLANNED",
            notes=user_message
        )
        db.add(fut)
        db.commit()

        if explicit_chart:
            all_future = (
                db.query(models.FutureExpense.item, models.FutureExpense.expected_amount)
                .filter(models.FutureExpense.status == "PLANNED")
                .order_by(models.FutureExpense.target_date.asc())
                .all()
            )
            chart_payload = {
                "type": "bar",
                "title": "Upcoming Future Planned Expenses",
                "data": [{"name": f[0], "value": round(float(f[1]), 2)} for f in all_future]
            }

        reply = f"📅 Stored future commitment: **{fut.item}** (₹{expected_amount:.2f}) scheduled for **{target_date.strftime('%b %d, %Y')}**."

    # -------------------------------------------------------------
    # 3. QUERY EXPENSES (Zero-Hallucination SQL Computation)
    # -------------------------------------------------------------
    elif intent == "QUERY_EXPENSES":
        time_filter = data.get("time_filter") or ("TODAY" if "today" in user_message.lower() else "ALL_TIME")
        chart_type = data.get("recommended_chart") or "pie"

        if time_filter == "FUTURE" or "future" in user_message.lower() or "upcoming" in user_message.lower():
            futs = (
                db.query(models.FutureExpense)
                .filter(models.FutureExpense.status == "PLANNED")
                .order_by(models.FutureExpense.target_date.asc())
                .all()
            )
            total_fut = sum(f.expected_amount for f in futs)
            if futs:
                items_list = "\n".join([f"• **{f.item}**: ₹{f.expected_amount:.2f} (Target: {f.target_date.strftime('%b %d, %Y')})" for f in futs])
                reply = f"You have **{len(futs)} planned commitment(s)** totaling **₹{total_fut:.2f}**:\n{items_list}"
                if explicit_chart:
                    chart_payload = {
                        "type": chart_type if chart_type in ["bar", "pie", "line"] else "bar",
                        "title": "Planned Future Commitments",
                        "data": [{"name": f.item, "value": round(float(f.expected_amount), 2)} for f in futs]
                    }
            else:
                reply = "No future expenses scheduled yet. Try: *'Plan ₹3000 for Car Insurance next month'*."

        elif target_category or target_item:
            query = db.query(models.Expense)
            is_yesterday = time_filter == "YESTERDAY" or bool(re.search(r'\b(yest[a-z]*|yesterdat|yesteday)\b', user_message.lower()))
            if is_yesterday:
                yest_d = date.today() - timedelta(days=1)
                query = query.filter(models.Expense.expense_date == yest_d)
                time_label = f"yesterday ({yest_d.strftime('%b %d')})"
            elif time_filter == "TODAY":
                query = query.filter(models.Expense.expense_date == date.today())
                time_label = "today"
            else:
                time_label = "overall"
            
            conditions = []
            if target_category:
                conditions.append(models.Expense.category.ilike(f"%{target_category}%"))
                conditions.append(models.Expense.item.ilike(f"%{target_category}%"))
            if target_item:
                conditions.append(models.Expense.item.ilike(f"%{target_item}%"))
            
            records = query.filter(or_(*conditions)).order_by(models.Expense.id.asc()).all()
            category_label = target_category or (target_item.title() if target_item else "Selected")

            if records:
                calculated_total = sum(r.amount for r in records)
                item_rows = "\n".join([f"• **{r.item}**: ₹{r.amount:.2f} *(Date: {r.expense_date})*" for r in records])
                reply = (
                    f"Calculated {time_label} **{category_label}** expenses:\n\n"
                    f"{item_rows}\n\n"
                    f"👉 **Total {category_label} Amount**: **₹{calculated_total:.2f}** (across {len(records)} record(s))."
                )

                # Check for remembered budget
                all_budgets = db.query(models.UserMemory).filter(
                    models.UserMemory.memory_type == "BUDGET"
                ).all()
                matched_budget = None
                cat_l = category_label.lower()
                for b in all_budgets:
                    b_top = b.topic.lower()
                    if any(stem in b_top and stem in cat_l for stem in ["grocer", "veg", "dairy", "milk", "food", "dining", "transport", "loan", "bill", "rent", "fee"]):
                        matched_budget = b
                        break
                    elif any(w in b_top for w in cat_l.split() if len(w) > 3):
                        matched_budget = b
                        break

                if matched_budget:
                    budget_nums = re.findall(r'(\d+(?:\.\d+)?)', matched_budget.content)
                    if budget_nums:
                        b_limit = float(budget_nums[0])
                        pct_used = (calculated_total / b_limit * 100) if b_limit > 0 else 0
                        rem = max(0.0, b_limit - calculated_total)
                        reply += (
                            f"\n\n🎯 **Remembered Budget Tracker**:\n"
                            f"• Target Budget: **₹{b_limit:,.2f}**\n"
                            f"• Consumed: **{pct_used:.0f}%** (₹{calculated_total:,.2f})\n"
                            f"• Remaining Available: **₹{rem:,.2f}**"
                        )

                if explicit_chart:
                    chart_payload = {
                        "type": chart_type if chart_type in ["bar", "pie", "line"] else "bar",
                        "title": f"{category_label} Expense Items ({time_label.title()})",
                        "data": [{"name": r.item, "value": round(float(r.amount), 2)} for r in records]
                    }
            else:
                reply = f"No records found for **{category_label}** {time_label}."

        elif time_filter == "TODAY":
            today_records = (
                db.query(models.Expense)
                .filter(models.Expense.expense_date == date.today())
                .order_by(models.Expense.id.asc())
                .all()
            )
            total_today = sum(e.amount for e in today_records)

            if today_records:
                items_str = "\n".join([f"• **{e.item}** ({e.category}): ₹{e.amount:.2f}" for e in today_records])
                reply = f"Today's total spend is **₹{total_today:.2f}** across {len(today_records)} items:\n{items_str}"

                if explicit_chart:
                    cat_summary = (
                        db.query(models.Expense.category, func.sum(models.Expense.amount))
                        .filter(models.Expense.expense_date == date.today())
                        .group_by(models.Expense.category)
                        .all()
                    )
                    chart_payload = {
                        "type": chart_type if chart_type in ["pie", "bar", "line"] else "pie",
                        "title": f"Today's Spend Breakdown ({date.today().strftime('%b %d')})",
                        "data": [{"name": cat, "value": round(float(amt), 2)} for cat, amt in cat_summary]
                    }
            else:
                reply = "No expenses recorded for today yet. Tell me what you bought (e.g. *'Milk 30 and Veggies 70'*)."

        else:
            cat_summary = (
                db.query(models.Expense.category, func.sum(models.Expense.amount))
                .group_by(models.Expense.category)
                .all()
            )
            total_all = sum(float(amt) for _, amt in cat_summary)

            if cat_summary:
                cat_lines = "\n".join([f"• **{cat}**: ₹{float(amt):.2f}" for cat, amt in cat_summary])
                reply = f"Total tracked spending is **₹{total_all:.2f}** across {len(cat_summary)} categories:\n{cat_lines}"
                
                if explicit_chart:
                    chart_payload = {
                        "type": chart_type if chart_type in ["pie", "bar", "line"] else "pie",
                        "title": "Expense Distribution by Category",
                        "data": [{"name": cat, "value": round(float(amt), 2)} for cat, amt in cat_summary]
                    }
            else:
                reply = "No expense data recorded yet. Start by entering your expenses!"

    # -------------------------------------------------------------
    # 4. PREDICT & FORECAST EXPENSES (Run-Rate & Machine Forecasting)
    # -------------------------------------------------------------
    elif intent == "PREDICT_EXPENSES":
        all_expenses = db.query(models.Expense).all()
        planned_futs = db.query(models.FutureExpense).filter(models.FutureExpense.status == "PLANNED").all()

        if not all_expenses and not planned_futs:
            reply = "🔮 **Predictive Forecasting**: No historical expenses or scheduled commitments found yet to project from. Add a few expenses (e.g. *'Milk 45, Groceries 1200'*) or commitments to generate a forecast!"
            chart_payload = None
        elif target_category or target_item:
            # Specific category forecast
            conditions = []
            if target_category:
                conditions.append(models.Expense.category.ilike(f"%{target_category}%"))
                conditions.append(models.Expense.item.ilike(f"%{target_category}%"))
            if target_item:
                conditions.append(models.Expense.item.ilike(f"%{target_item}%"))
            
            cat_records = db.query(models.Expense).filter(or_(*conditions)).all()
            cat_label = target_category or (target_item.title() if target_item else "Selected Category")

            if not cat_records:
                reply = f"🔮 **Forecast for {cat_label}**: No past recorded transactions found in **{cat_label}** to project future spending."
                chart_payload = None
            else:
                total_cat_spent = sum(r.amount for r in cat_records)
                dates_count = len(set(r.expense_date for r in cat_records)) or 1
                daily_avg = total_cat_spent / dates_count

                is_fixed_monthly = any(c in cat_label.lower() for c in ['loan', 'emi', 'school', 'fee', 'rent', 'bill', 'insurance'])
                if is_fixed_monthly:
                    projected_30d = total_cat_spent
                    run_rate_label = f"₹{projected_30d:.2f} per monthly cycle"
                else:
                    projected_30d = daily_avg * 30
                    run_rate_label = f"₹{daily_avg:.2f}/day (based on {dates_count} active tracking day(s))"

                week1 = round(projected_30d * 0.25, 2)
                week2 = round(projected_30d * 0.50, 2)
                week3 = round(projected_30d * 0.75, 2)
                week4 = round(projected_30d, 2)

                reply = (
                    f"🔮 **AI Expense Forecast for {cat_label}**:\n\n"
                    f"• **Current Recorded Spend**: ₹{total_cat_spent:.2f}\n"
                    f"• **Estimated Run-Rate**: {run_rate_label}\n"
                    f"• **Projected 30-Day Expense**: **₹{projected_30d:.2f}**\n\n"
                    f"💡 **Predictive Insight**: At this baseline velocity, you are projected to spend approximately **₹{projected_30d:.2f}** on {cat_label} over the next 30 days."
                )

                chart_payload = {
                    "type": "line" if data.get("recommended_chart") == "line" else "bar",
                    "title": f"Projected 4-Week Cumulative Spend: {cat_label} (₹)",
                    "data": [
                        {"name": "Week 1", "value": week1},
                        {"name": "Week 2", "value": week2},
                        {"name": "Week 3", "value": week3},
                        {"name": "Week 4 (End)", "value": week4}
                    ]
                }
        else:
            # Comprehensive Next-Month Financial Forecast
            cat_totals = {}
            for e in all_expenses:
                cat_totals[e.category] = cat_totals.get(e.category, 0.0) + e.amount

            fixed_categories = {"Loans & EMI", "Education & Fees", "Bills & Utilities", "Rent"}
            projected_by_cat = {}
            total_fixed = 0.0
            total_variable = 0.0

            for cat, amt in cat_totals.items():
                if cat in fixed_categories or "loan" in cat.lower() or "fee" in cat.lower():
                    proj = amt
                    total_fixed += proj
                    projected_by_cat[cat] = proj
                else:
                    if amt > 2000:
                        proj = amt
                    else:
                        proj = amt * 10 if amt > 200 else amt * 30
                    total_variable += proj
                    projected_by_cat[cat] = proj

            total_planned_futs = sum(f.expected_amount for f in planned_futs)
            if total_planned_futs > 0:
                projected_by_cat["Scheduled Commitments"] = total_planned_futs
                total_fixed += total_planned_futs

            total_projected_next_month = sum(projected_by_cat.values())
            fixed_pct = (total_fixed / total_projected_next_month * 100) if total_projected_next_month > 0 else 0
            variable_pct = 100 - fixed_pct

            sorted_cats = sorted(projected_by_cat.items(), key=lambda x: x[1], reverse=True)
            top_driver_name, top_driver_amt = sorted_cats[0] if sorted_cats else ("Expenses", 0)
            top_driver_pct = (top_driver_amt / total_projected_next_month * 100) if total_projected_next_month > 0 else 0

            breakdown_lines = "\n".join([f"• **{k}**: ₹{v:,.2f}" for k, v in sorted_cats])

            reply = (
                f"🔮 **Next Month Financial Forecast & Expense Prediction**:\n\n"
                f"Based on your recurring ledger patterns and planned commitments, here is your projected spending for next month:\n\n"
                f"{breakdown_lines}\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👉 **Total Projected Spend**: **₹{total_projected_next_month:,.2f}**\n\n"
                f"📊 **Financial Burn-Rate Analysis**:\n"
                f"• **Fixed Commitments (Loans, Fees, Scheduled Bills)**: ₹{total_fixed:,.2f} ({fixed_pct:.0f}%)\n"
                f"• **Flexible Daily Essentials (Dairy, Groceries, Dining)**: ₹{total_variable:,.2f} ({variable_pct:.0f}%)\n"
                f"• **Primary Cost Driver**: **{top_driver_name}** represents **{top_driver_pct:.0f}%** of your projected outflow.\n\n"
                f"💡 **Autonomous Advisory**: To optimize your savings next month, focusing on discretionary daily spending can preserve up to **15-20%** of your flexible budget."
            )

            # Check remembered income/salary
            salary_mem = db.query(models.UserMemory).filter(
                models.UserMemory.memory_type == "INCOME"
            ).first()
            if salary_mem:
                salary_nums = re.findall(r'(\d+(?:\.\d+)?)', salary_mem.content)
                if salary_nums:
                    salary_amt = float(salary_nums[0])
                    projected_savings = salary_amt - total_projected_next_month
                    savings_rate = (projected_savings / salary_amt * 100) if salary_amt > 0 else 0
                    reply += (
                        f"\n\n💰 **Income vs. Projected Outflow (from Remembered Salary)**:\n"
                        f"• Monthly Income: **₹{salary_amt:,.2f}**\n"
                        f"• Projected Monthly Savings: **₹{projected_savings:,.2f}** ({savings_rate:.0f}% savings rate)"
                    )

            chart_payload = {
                "type": data.get("recommended_chart") or "bar",
                "title": f"Projected Next Month Budget Allocation (Total: ₹{total_projected_next_month:,.0f})",
                "data": [{"name": k, "value": round(float(v), 2)} for k, v in sorted_cats]
            }

    # -------------------------------------------------------------
    # 5. REMEMBER (Persistent Financial Profile / Long-Term Memory)
    # -------------------------------------------------------------
    elif intent == "REMEMBER":
        mem_data = data.get("memory", {})
        topic = mem_data.get("topic") or "Financial Preference"
        content = mem_data.get("content") or user_message
        mem_type = mem_data.get("memory_type") or "PREFERENCE"

        existing = db.query(models.UserMemory).filter(models.UserMemory.topic.ilike(f"%{topic}%")).first()
        if existing:
            existing.content = content
            existing.memory_type = mem_type
            existing.updated_at = datetime.utcnow()
            action_verb = "Updated"
        else:
            new_mem = models.UserMemory(
                topic=topic,
                content=content,
                memory_type=mem_type
            )
            db.add(new_mem)
            action_verb = "Saved"
        db.commit()

        reply = (
            f"🧠 **Memory {action_verb} in Your Financial Profile**:\n\n"
            f"• **Topic**: **{topic}**\n"
            f"• **Detail**: *\"{content}\"*\n"
            f"• **Type**: `{mem_type}`\n\n"
            f"💡 **Context Active**: I've saved this permanently in your cloud ledger. I will automatically reference it when calculating budgets, checking expense limits, and generating predictions."
        )

    # -------------------------------------------------------------
    # 6. RECALL_MEMORY (Recall Saved Profile)
    # -------------------------------------------------------------
    elif intent == "RECALL_MEMORY":
        memories = db.query(models.UserMemory).order_by(models.UserMemory.id.asc()).all()
        if not memories:
            reply = (
                "🧠 **Financial Memory Profile**:\n\n"
                "I haven't stored any personal financial preferences yet!\n\n"
                "You can tell me things like:\n"
                "• *'Remember that my monthly grocery budget is ₹8,000'*\n"
                "• *'Remember my monthly salary is ₹65,000 credited on the 1st'*\n"
                "• *'Remember my car loan EMI of ₹12,000 is due on the 5th'*\n"
                "• *'Remember I prefer organic milk from Nandini'*"
            )
        else:
            type_icons = {
                "BUDGET": "🎯",
                "INCOME": "💰",
                "RECURRING_BILL": "📅",
                "PREFERENCE": "⭐",
                "GOAL": "🏆",
                "NOTE": "📝"
            }
            mem_lines = []
            for m in memories:
                icon = type_icons.get(m.memory_type, "📌")
                date_str = m.updated_at.strftime('%b %d') if m.updated_at else ""
                mem_lines.append(f"• {icon} **{m.topic}**: {m.content} *(Saved {date_str})*")

            reply = (
                f"🧠 **Your Remembered Financial Profile** ({len(memories)} active memory item(s)):\n\n"
                + "\n".join(mem_lines)
                + "\n\n💡 *I actively reference these memories when analyzing your spending burn-rates and projecting next-month budgets.*"
            )

    # -------------------------------------------------------------
    # 7. FORGET_MEMORY (Clear or Remove Memory)
    # -------------------------------------------------------------
    elif intent == "FORGET_MEMORY":
        topic_target = data.get("topic_target", "")
        if not topic_target or "all" in topic_target.lower():
            count = db.query(models.UserMemory).delete()
            db.commit()
            reply = f"🧠 **Memories Cleared**: Successfully wiped {count} remembered item(s) from your financial profile."
        else:
            deleted = db.query(models.UserMemory).filter(models.UserMemory.topic.ilike(f"%{topic_target}%")).delete()
            db.commit()
            if deleted:
                reply = f"🧠 **Memory Removed**: Forgot all notes related to **{topic_target}**."
            else:
                reply = f"🧠 No saved memory matching **'{topic_target}'** was found in your profile."

    else:
        reply = data.get("reply_text") or "I can help you track and calculate your expenses!"

    # Smart Suggested Questions
    suggestions = [
        {"question": "What do you remember about my finances?", "tooltip": "Inspect active memories & financial profile"},
        {"question": "Remember that my grocery budget is ₹8,000 per month", "tooltip": "Store long-term budget constraint"},
        {"question": "Predict my next month expenses", "tooltip": "AI forecast based on recurring run-rate & commitments"},
        {"question": "Calculate today dairy amount", "tooltip": "Calculates strictly Dairy records"}
    ]

    return {
        "reply": reply,
        "chart": chart_payload,
        "suggestions": suggestions,
        "db_type": "Cloud Active"
    }
