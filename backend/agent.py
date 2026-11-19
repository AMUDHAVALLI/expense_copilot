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
All data is stored and retrieved strictly from PostgreSQL.

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
   - "wants_chart": true ONLY if the user explicitly used words like 'chart', 'graph', 'pie', 'bar', 'plot', 'visualize'. Otherwise false.

Respond strictly in valid JSON matching this schema:
{{
  "intent": "ADD_TODAY_EXPENSE" | "ADD_FUTURE_EXPENSE" | "QUERY_EXPENSES" | "GENERAL",
  "expense_date": "YYYY-MM-DD" | null,
  "items": [
    {{"item": "Milk", "category": "Dairy", "amount": 500.0}},
    {{"item": "Personal Loan", "category": "Loans & EMI", "amount": 20.0}}
  ],
  "future_item": {{"item": "Bike Service", "category": "Bills & Utilities", "expected_amount": 3500.0, "target_date": "YYYY-MM-DD"}},
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

def parse_date_from_message(text: str) -> date:
    """Parses date context from the user message."""
    t = text.lower()
    if "last month" in t:
        # 15th of the previous month
        first_of_this_month = date.today().replace(day=1)
        last_month_end = first_of_this_month - timedelta(days=1)
        return last_month_end.replace(day=15)
    elif "yesterday" in t:
        return date.today() - timedelta(days=1)
    return date.today()

def extract_all_expenses(text: str) -> List[Dict[str, Any]]:
    """
    Robust multi-strategy parser that splits lists by comma, 'and', semicolons,
    and extracts EVERY single expense item and amount without skipping any.
    """
    # Clean string
    cleaned = text.strip()
    # Normalize common connectors
    chunks = re.split(r'[,;\n]|(?:\band\b)', cleaned)
    items = []

    for chunk in chunks:
        c = chunk.strip()
        if not c:
            continue
        
        # Remove leading boilerplate
        c = re.sub(r'^(?:last\s+month\s+|this\s+month\s+|today\s+|yesterday\s+)?(?:i\s+)?(?:spent|bought|paid|gave|give|given)\s+', '', c, flags=re.I).strip()
        # Remove trailing boilerplate
        c = re.sub(r'\s+(?:i\s+have\s+given|given|i\s+gave)$', '', c, flags=re.I).strip()

        # Strategy 1: (rs|inr)? <amount> (rs|inr)? (for|on|of) <item>
        # e.g. "rs 500 for milk", "500 for milk"
        m1 = re.search(r'^(?:rs\.?|inr|₹|\$)?\s*(\d+(?:\.\d+)?)\s*(?:rs\.?|inr|₹|\$)?\s*(?:for|on|of)\s+([a-zA-Z\s]+)$', c, flags=re.I)
        if m1:
            itm = m1.group(2).strip().title()
            amt = float(m1.group(1))
            if itm and amt > 0:
                items.append({"item": itm, "category": detect_category(itm), "amount": amt})
                continue

        # Strategy 2: <item> (?:for|on|of|is|:|-)? (rs|inr)? <amount> (rs|inr)?
        # e.g. "perosonal loan for 20 rs", "school fess 2500", "supplement for rs6000", "home loan for rs20000", "Groceries 5000", "vegtable for 500", "snack for 300"
        m2 = re.search(r'^([a-zA-Z\s]+?)\s*(?:for|on|of|is|:|-)?\s*(?:rs\.?|inr|₹|\$)?\s*(\d+(?:\.\d+)?)\s*(?:rs\.?|inr|₹|\$)?$', c, flags=re.I)
        if m2:
            itm = m2.group(1).strip().title()
            amt = float(m2.group(2))
            if itm and amt > 0:
                items.append({"item": itm, "category": detect_category(itm), "amount": amt})
                continue

        # Strategy 3: Flexible fallback regex: find digits and words
        dm = re.search(r'(\d+(?:\.\d+)?)', c)
        if dm:
            amt = float(dm.group(1))
            itm = re.sub(r'\b(rs\.?|inr|for|on|of|spent|paid|bought|today|yesterday|last month|given)\b|[₹\$]', '', c, flags=re.I)
            itm = re.sub(r'\d+(?:\.\d+)?', '', itm).strip().title()
            if itm and amt > 0:
                items.append({"item": itm, "category": detect_category(itm), "amount": amt})

    return items

def heuristic_fallback_parse(user_message: str) -> Dict[str, Any]:
    """Smart parser when OpenAI is unavailable or for instant local fallback."""
    msg = user_message.strip()
    msg_lower = msg.lower()
    wants_chart = user_explicitly_wants_chart(msg)

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
        time_filt = "FUTURE" if ("future" in msg_lower or "upcoming" in msg_lower) else ("TODAY" if "today" in msg_lower else "ALL_TIME")
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
        return {
            "intent": "ADD_TODAY_EXPENSE",
            "expense_date": parse_date_from_message(msg).strftime("%Y-%m-%d"),
            "wants_chart": wants_chart,
            "recommended_chart": "pie" if wants_chart else None,
            "items": items,
            "reply_text": ""
        }

    return {
        "intent": "GENERAL",
        "wants_chart": False,
        "recommended_chart": None,
        "reply_text": "I can help you track and calculate your expenses from PostgreSQL! Try entering your expenses or asking questions."
    }

def process_chat(user_message: str, db: Session) -> Dict[str, Any]:
    data = None

    try:
        if not openai_client:
            raise ValueError("OpenAI client not configured")
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0
        )
        data = json.loads(response.choices[0].message.content)
    except Exception:
        data = heuristic_fallback_parse(user_message)

    # Double-check: ensure NO items were dropped by LLM
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

        # Determine target date
        target_date_val = parse_date_from_message(user_message)
        if data.get("expense_date"):
            try:
                target_date_val = datetime.strptime(data["expense_date"], "%Y-%m-%d").date()
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

        date_label = "Last Month" if "last month" in user_message.lower() else target_date_val.strftime('%b %d, %Y')
        reply = (
            f"✅ Successfully stored all **{len(saved_items)} item(s)** in PostgreSQL ({date_label}):\n\n"
            + "\n".join(saved_items)
            + f"\n\n👉 **Total Recorded**: **₹{total_amount:.2f}**"
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

        reply = f"📅 Stored future commitment in PostgreSQL: **{fut.item}** (₹{expected_amount:.2f}) scheduled for **{target_date.strftime('%b %d, %Y')}**."

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
                reply = f"You have **{len(futs)} planned future expense(s)** in PostgreSQL totaling **₹{total_fut:.2f}**:\n{items_list}"
                if explicit_chart:
                    chart_payload = {
                        "type": chart_type if chart_type in ["bar", "pie", "line"] else "bar",
                        "title": "Planned Future Commitments",
                        "data": [{"name": f.item, "value": round(float(f.expected_amount), 2)} for f in futs]
                    }
            else:
                reply = "No future expenses scheduled yet in PostgreSQL. Try: *'Plan ₹3000 for Car Insurance next month'*."

        elif target_category or target_item:
            query = db.query(models.Expense)
            if time_filter == "TODAY":
                query = query.filter(models.Expense.expense_date == date.today())
            
            conditions = []
            if target_category:
                conditions.append(models.Expense.category.ilike(f"%{target_category}%"))
                conditions.append(models.Expense.item.ilike(f"%{target_category}%"))
            if target_item:
                conditions.append(models.Expense.item.ilike(f"%{target_item}%"))
            
            records = query.filter(or_(*conditions)).order_by(models.Expense.id.asc()).all()
            category_label = target_category or (target_item.title() if target_item else "Selected")
            time_label = "today" if time_filter == "TODAY" else "overall"

            if records:
                calculated_total = sum(r.amount for r in records)
                item_rows = "\n".join([f"• **{r.item}**: ₹{r.amount:.2f} *(Date: {r.expense_date})*" for r in records])
                reply = (
                    f"Calculated {time_label} **{category_label}** amount from PostgreSQL:\n\n"
                    f"{item_rows}\n\n"
                    f"👉 **Total {category_label} Amount**: **₹{calculated_total:.2f}** (across {len(records)} record(s))."
                )

                if explicit_chart:
                    chart_payload = {
                        "type": chart_type if chart_type in ["bar", "pie", "line"] else "bar",
                        "title": f"{category_label} Expense Items ({time_label.title()})",
                        "data": [{"name": r.item, "value": round(float(r.amount), 2)} for r in records]
                    }
            else:
                reply = f"No records found in PostgreSQL for **{category_label}** {time_label}."

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
                reply = "No expenses recorded in PostgreSQL for today yet. Tell me what you bought (e.g. *'Milk 30 and Veggies 70'*)."

        else:
            cat_summary = (
                db.query(models.Expense.category, func.sum(models.Expense.amount))
                .group_by(models.Expense.category)
                .all()
            )
            total_all = sum(float(amt) for _, amt in cat_summary)

            if cat_summary:
                cat_lines = "\n".join([f"• **{cat}**: ₹{float(amt):.2f}" for cat, amt in cat_summary])
                reply = f"Total tracked spending in PostgreSQL is **₹{total_all:.2f}** across {len(cat_summary)} categories:\n{cat_lines}"
                
                if explicit_chart:
                    chart_payload = {
                        "type": chart_type if chart_type in ["pie", "bar", "line"] else "pie",
                        "title": "Expense Distribution by Category",
                        "data": [{"name": cat, "value": round(float(amt), 2)} for cat, amt in cat_summary]
                    }
            else:
                reply = "No expense data recorded in PostgreSQL yet. Start by entering today's expenses!"

    else:
        reply = data.get("reply_text") or "I can help you track and calculate your expenses from PostgreSQL!"

    # Smart Suggested Questions
    suggestions = [
        {"question": "Calculate today dairy amount", "tooltip": "Calculates strictly Dairy records from PostgreSQL"},
        {"question": "What did I spend today?", "tooltip": "Shows today's total spending"},
        {"question": "Show pie chart of expenses", "tooltip": "Requests visual chart of all categories"},
        {"question": "Show future planned expenses", "tooltip": "Lists upcoming scheduled commitments"}
    ]

    return {
        "reply": reply,
        "chart": chart_payload,
        "suggestions": suggestions,
        "db_type": "PostgreSQL"
    }
