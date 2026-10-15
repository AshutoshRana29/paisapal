# PaisaPal: The Personal Expense & Budget Coach

**Task Code:** T3  
**Agent Name:** PaisaPal  
**Team:** (Your Team Name)

A simple AI agent that lets users log expenses in plain English, track monthly spending, and manage budgets. All data is stored in a real SQLite database.

---

## What this project does

Users talk to **PaisaPal** in natural language

like:

- "Spent 250 on food yesterday"
- "How much did I spend on food this month?"
- "Set my shopping budget to 3000"
- "Am I over budget anywhere?"

The agent extracts amount, category, and date, stores it in the database, and answers questions by querying the data.

---

## Setup

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
sqlite3 paisapal.db < schema.sql
python seed.py

# make .env and get your API key from groq
copy .env.example .env
# Edit .env and put your real API key

#Run the agent
python agent.py
```

**Mac/Linux:**

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sqlite3 paisapal.db < schema.sql
python seed.py
cp .env.example .env
```

---

## What it can do

- Log expenses/income from normal sentences
- Show spending by category
- Set and check budgets (warns at ~80% and 100%)
- List transactions
- Delete a transaction (asks for confirmation)
- Support multiple users

---

## Notes

- Understands dates like “yesterday”, “today”, “last Monday”
- Amounts must be positive
- See test_prompts.md for test cases

---
