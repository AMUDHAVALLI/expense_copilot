# 💼 Expense Copilot AI — Interview Demo Guide

A production-grade, enterprise **Financial Copilot Chatbot** built with **React, Tailwind CSS, Python (FastAPI), and PostgreSQL**.

---

## 🎯 How to Present in Your Interview

### 1. The Core Problem It Solves
Traditional chatbots suffer from **hallucination** when answering numerical or financial questions.  
**Expense Copilot solves this** by executing strict SQL aggregation directly on PostgreSQL. The LLM acts purely as a semantic intent parser; the numbers are calculated deterministically by PostgreSQL.

---

### 2. Live Demo Script (Step-by-Step)

| Step | Action / Question to Ask | What the Interviewer Sees |
| :--- | :--- | :--- |
| **1. Seed Demo Data** | Click **"⚡ Seed Demo"** in the top bar | Resets database and populates clean, realistic data across Dairy, Groceries, Dining, Transport, and Future Bills. Live badges update immediately. |
| **2. Category Aggregation (No Hallucination)** | Click quick filter **"🥛 Dairy"** or ask: *`Calculate today dairy amount`* | It queries PostgreSQL specifically for Dairy items (`Milk (2L)` + `Paneer & Curd`) and calculates **₹184.00**. No unrelated categories (veggies, petrol) appear! |
| **3. Live Natural Language Insertion** | Type: *`Spent 50 on coffee and 140 on fruits today`* | Instantly recorded to PostgreSQL. The top-bar stats update automatically in real-time. |
| **4. Future Expense Forecasting** | Click **"📅 Future"** or ask: *`Plan ₹4500 for Bike Insurance on Dec 15`* | Extracts target date and expected amount, stores in `future_expenses`, and displays upcoming commitments. |
| **5. On-Demand Dynamic Visualizations** | Click **"📊 Chart"** or ask: *`Show pie chart of my expenses`* | An inline interactive chart appears. **Click between [Pie], [Bar], and [Trend]** right on the chart to demonstrate dynamic rendering! |

---

## 🚀 How to Launch the Demo

Double-click:
👉 **`run_all.bat`**

- **Frontend**: http://localhost:5173
- **FastAPI Docs**: http://127.0.0.1:8000/docs
- **Database**: PostgreSQL (`expense_copilot`)
